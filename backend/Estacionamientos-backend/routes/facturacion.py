import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from fastapi.responses import Response

from core.invoice_provider import IssueInvoiceInput, get_invoice_provider
from core.public_security import enforce_rate_limit_or_raise, verify_recaptcha_or_raise
from database import get_db
from models.fiscal_customer import FiscalCustomer
from models.history_estacionamiento import HistoryEstacionamiento
from models.invoice_document import InvoiceDocument
from models.invoice_event import InvoiceEvent
from models.invoice_request import InvoiceRequest
from schemas.facturacion import (
    InvoiceCancelRequest,
    InvoiceCancelResponse,
    InvoiceEmitRequest,
    InvoiceEmitResponse,
    InvoiceRequestStatusResponse,
)
from schemas.fiscal_customer import FiscalCustomerResponse, FiscalCustomerUpsertRequest


router = APIRouter()


def _env_int(name: str, default: int, min_value: int, max_value: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = default
    return max(min_value, min(max_value, parsed))


def _get_ticket_max_age_hours() -> int:
    return _env_int("FACTURACION_TICKET_MAX_AGE_HOURS", 72, 1, 24 * 30)


def _get_clientes_fiscales_post_limit() -> int:
    return _env_int("FACTURACION_RL_CLIENTES_FISCALES_POST_PER_MIN", 5, 1, 300)


def _get_emitir_post_limit() -> int:
    return _env_int("FACTURACION_RL_EMITIR_POST_PER_MIN", 3, 1, 300)


def _validate_ticket_for_facturacion(
    db: Session,
    history_estacionamiento_id: int,
    placa: str,
    fecha_salida,
    hora_salida,
    importe: float,
) -> HistoryEstacionamiento:
    history = db.query(HistoryEstacionamiento).filter(HistoryEstacionamiento.id == history_estacionamiento_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Movimiento historico no encontrado")

    if not bool(history.pagado):
        raise HTTPException(status_code=400, detail="El movimiento historico no esta pagado")

    if int(getattr(history, "cancelado", 0)) == 1:
        raise HTTPException(status_code=409, detail="El movimiento historico esta cancelado y no puede facturarse")

    if not history.placa or not history.fecha_salida or not history.hora_salida:
        raise HTTPException(status_code=400, detail="El ticket historico no tiene datos suficientes para facturacion")

    if history.placa.strip().upper() != placa:
        raise HTTPException(status_code=400, detail="La placa no coincide con el ticket historico")
    if history.fecha_salida != fecha_salida:
        raise HTTPException(status_code=400, detail="La fecha_salida no coincide con el ticket historico")
    if history.hora_salida != hora_salida:
        raise HTTPException(status_code=400, detail="La hora_salida no coincide con el ticket historico")
    if abs(float(history.importe) - float(importe)) > 0.01:
        raise HTTPException(status_code=400, detail="El importe no coincide con el ticket historico")

    ticket_timestamp = datetime.combine(history.fecha_salida, history.hora_salida)
    if datetime.utcnow() - ticket_timestamp > timedelta(hours=_get_ticket_max_age_hours()):
        raise HTTPException(status_code=400, detail="El ticket ya excedio la ventana permitida para facturacion")

    existing_invoice = (
        db.query(InvoiceRequest)
        .filter(
            InvoiceRequest.source_type == InvoiceRequest.SOURCE_HISTORY_EXIT,
            InvoiceRequest.source_id == str(history.id),
            InvoiceRequest.status.in_([InvoiceRequest.STATUS_PROCESSING, InvoiceRequest.STATUS_ISSUED]),
        )
        .first()
    )
    if existing_invoice:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TICKET_ALREADY_INVOICED",
                "message": "Este ticket ya tiene una factura emitida o en proceso",
                "existing_invoice_request_id": existing_invoice.id,
            },
        )

    return history


def _build_idempotency_key(rfc: str, source_type: str, source_id: str, total: float) -> str:
    fingerprint = f"{rfc}|{source_type}|{source_id}|{round(float(total), 2)}"
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"{source_type}-{source_id}-{digest[:20]}"


def _get_access_token_ttl_hours() -> int:
    raw_value = os.getenv("FACTURACION_ACCESS_TOKEN_TTL_HOURS", "168").strip()
    try:
        ttl = int(raw_value)
    except ValueError:
        ttl = 168
    return max(1, min(ttl, 24 * 30))


def _generate_access_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_access_token(access_token: str) -> str:
    pepper = os.getenv("FACTURACION_ACCESS_TOKEN_PEPPER", "").strip()
    payload = f"{access_token}|{pepper}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_access_token(access_token: str | None, x_invoice_access_token: str | None) -> str:
    token = (x_invoice_access_token or access_token or "").strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token de acceso requerido para consultar o descargar esta factura",
        )
    return token


def _authorize_invoice_access(invoice_request: InvoiceRequest, token: str) -> None:
    if not invoice_request.access_token_hash:
        raise HTTPException(
            status_code=403,
            detail="Solicitud sin token de acceso. Genera una nueva solicitud para habilitar acceso seguro",
        )

    if invoice_request.access_token_expires_at and invoice_request.access_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token de acceso expirado")

    expected_hash = _hash_access_token(token)
    if not hmac.compare_digest(invoice_request.access_token_hash, expected_hash):
        raise HTTPException(status_code=403, detail="Token de acceso invalido")


def _mask_email(email: str | None) -> str | None:
    if not email:
        return None
    email_norm = email.strip()
    if "@" not in email_norm:
        return None
    local, domain = email_norm.split("@", 1)
    if len(local) <= 2:
        return f"**@{domain}"
    return f"{local[:2]}***@{domain}"


def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    compact = "".join(ch for ch in phone if ch.isdigit())
    if len(compact) <= 2:
        return "**"
    return f"***{compact[-2:]}"


def _public_fiscal_customer_response(customer: FiscalCustomer) -> FiscalCustomerResponse:
    return FiscalCustomerResponse(
        id=customer.id,
        rfc=customer.rfc,
        razon_social=customer.razon_social,
        codigo_postal=customer.codigo_postal,
        regimen_fiscal=customer.regimen_fiscal,
        uso_cfdi_receptor=customer.uso_cfdi_receptor,
        nombre_contacto=None,
        email=_mask_email(customer.email),
        telefono=_mask_phone(customer.telefono),
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


def _payment_form_from_metodo_pago(metodo_pago: str) -> str:
    metodo = (metodo_pago or "").strip().lower()
    mapping = {
        "efectivo": "01",
        "cash": "01",
        "tarjeta": "04",
        "card": "04",
        "debito": "28",
        "débito": "28",
        "credito": "04",
        "crédito": "04",
    }
    return mapping.get(metodo, "01")


def _event(db: Session, invoice_request_id: int, event_type: str, payload: dict | None = None, success: bool = True, error_message: str | None = None) -> None:
    db.add(
        InvoiceEvent(
            invoice_request_id=invoice_request_id,
            event_type=event_type,
            payload_summary_json=InvoiceEvent.build_payload(payload or {}),
            success=success,
            error_message=error_message,
        )
    )


@router.get("/clientes-fiscales/por-rfc/{rfc}", response_model=FiscalCustomerResponse)
def get_fiscal_customer_by_rfc(rfc: str, db: Session = Depends(get_db)):
    rfc_norm = rfc.strip().upper()
    customer = db.query(FiscalCustomer).filter(FiscalCustomer.rfc == rfc_norm, FiscalCustomer.is_active == True).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "FISCAL_CUSTOMER_NOT_FOUND",
                "message": f"Cliente fiscal con RFC {rfc_norm} no encontrado",
            },
        )
    return _public_fiscal_customer_response(customer)


@router.post("/clientes-fiscales", response_model=FiscalCustomerResponse)
def upsert_fiscal_customer(payload: FiscalCustomerUpsertRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit_or_raise(
        request=request,
        scope="facturacion:clientes-fiscales:post",
        limit_per_window=_get_clientes_fiscales_post_limit(),
        window_seconds=60,
    )
    verify_recaptcha_or_raise(request=request, token=payload.recaptcha_token, expected_action="registro_fiscal")

    _validate_ticket_for_facturacion(
        db=db,
        history_estacionamiento_id=payload.history_estacionamiento_id,
        placa=payload.placa,
        fecha_salida=payload.fecha_salida,
        hora_salida=payload.hora_salida,
        importe=payload.importe,
    )

    existing = db.query(FiscalCustomer).filter(FiscalCustomer.rfc == payload.rfc).first()

    if existing:
        existing.razon_social = payload.razon_social
        existing.codigo_postal = payload.codigo_postal
        existing.regimen_fiscal = payload.regimen_fiscal
        existing.uso_cfdi_receptor = payload.uso_cfdi_receptor
        existing.nombre_contacto = payload.nombre_contacto
        existing.email = payload.email
        existing.telefono = payload.telefono
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return _public_fiscal_customer_response(existing)

    customer = FiscalCustomer(
        rfc=payload.rfc,
        razon_social=payload.razon_social,
        codigo_postal=payload.codigo_postal,
        regimen_fiscal=payload.regimen_fiscal,
        uso_cfdi_receptor=payload.uso_cfdi_receptor,
        nombre_contacto=payload.nombre_contacto,
        email=payload.email,
        telefono=payload.telefono,
        is_active=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return _public_fiscal_customer_response(customer)


# TODO(refactor): Extraer este flujo a un servicio de aplicación para separar capa HTTP de reglas de negocio/persistencia.
@router.post("/emitir", response_model=InvoiceEmitResponse)
def emitir_factura(payload: InvoiceEmitRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit_or_raise(
        request=request,
        scope="facturacion:emitir:post",
        limit_per_window=_get_emitir_post_limit(),
        window_seconds=60,
    )
    verify_recaptcha_or_raise(request=request, token=payload.recaptcha_token, expected_action="emitir_factura")

    customer = db.query(FiscalCustomer).filter(
        FiscalCustomer.id == payload.fiscal_customer_id,
        FiscalCustomer.is_active == True,
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente fiscal no encontrado")

    source_type = InvoiceRequest.SOURCE_MANUAL
    source_id = ""
    amount = 0.0
    description = "Servicio de estacionamiento"

    history = _validate_ticket_for_facturacion(
        db=db,
        history_estacionamiento_id=payload.history_estacionamiento_id,
        placa=payload.placa,
        fecha_salida=payload.fecha_salida,
        hora_salida=payload.hora_salida,
        importe=payload.importe,
    )

    source_type = InvoiceRequest.SOURCE_HISTORY_EXIT
    source_id = str(history.id)
    amount = float(history.importe)
    description = f"Estacionamiento placa {history.placa}"

    idempotency_key = _build_idempotency_key(customer.rfc, source_type, source_id, amount)

    existing_request = db.query(InvoiceRequest).filter(InvoiceRequest.idempotency_key == idempotency_key).first()
    if existing_request:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVOICE_ALREADY_EXISTS",
                "message": "Ya existe una solicitud para esta operacion",
                "existing_invoice_request_id": existing_request.id,
            },
        )

    access_token = _generate_access_token()
    access_token_expires_at = datetime.utcnow() + timedelta(hours=_get_access_token_ttl_hours())

    invoice_request = InvoiceRequest(
        fiscal_customer_id=customer.id,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        status=InvoiceRequest.STATUS_PROCESSING,
        total=amount,
        currency="MXN",
        provider_name="facturapi",
        access_token_hash=_hash_access_token(access_token),
        access_token_expires_at=access_token_expires_at,
        invoice_payload_json=InvoiceRequest.build_payload(
            {
                "send_email": payload.send_email,
                "notes": payload.notes,
            }
        ),
        attempts=0,
    )
    db.add(invoice_request)
    db.flush()

    _event(
        db=db,
        invoice_request_id=invoice_request.id,
        event_type="created",
        payload={
            "source_type": source_type,
            "source_id": source_id,
            "amount": amount,
        },
    )

    # TODO(refactor): Delimitar transacciones por etapa (request, emisión, documento, eventos) para mejorar rollback/reintentos.
    try:
        provider = get_invoice_provider(invoice_request.provider_name)
        provider_result = provider.issue_invoice(
            IssueInvoiceInput(
                external_id=f"invreq-{invoice_request.id}",
                customer={
                    "rfc": customer.rfc,
                    "razon_social": customer.razon_social,
                    "codigo_postal": customer.codigo_postal,
                    "regimen_fiscal": customer.regimen_fiscal,
                    "uso_cfdi_receptor": customer.uso_cfdi_receptor,
                    "email": customer.email,
                },
                amount=amount,
                currency="MXN",
                description=description,
                payment_form=_payment_form_from_metodo_pago(history.metodo_pago),
                send_email=payload.send_email,
            )
        )

        invoice_request.attempts += 1
        invoice_request.provider_invoice_id = provider_result.provider_invoice_id
        invoice_request.provider_customer_id = str(customer.id)
        invoice_request.provider_last_error = None

        if provider_result.status == InvoiceRequest.STATUS_ISSUED or provider_result.uuid_fiscal:
            invoice_request.status = InvoiceRequest.STATUS_ISSUED
            customer.last_invoiced_at = datetime.utcnow()

            doc = InvoiceDocument(
                invoice_request_id=invoice_request.id,
                uuid_fiscal=provider_result.uuid_fiscal,
                serie=provider_result.serie,
                folio=provider_result.folio,
                issued_at=datetime.fromisoformat(provider_result.issued_at.replace("Z", "+00:00")) if provider_result.issued_at else datetime.utcnow(),
                subtotal=provider_result.subtotal,
                taxes=provider_result.taxes,
                total=provider_result.total,
                currency=provider_result.currency or "MXN",
                xml_url=provider_result.xml_url,
                pdf_url=provider_result.pdf_url,
                verification_url=provider_result.verification_url,
                status=InvoiceDocument.STATUS_ISSUED,
            )
            db.add(doc)

            _event(
                db=db,
                invoice_request_id=invoice_request.id,
                event_type="issued",
                payload={
                    "provider_invoice_id": provider_result.provider_invoice_id,
                    "uuid": provider_result.uuid_fiscal,
                },
            )

            if payload.send_email and provider_result.provider_invoice_id:
                try:
                    email_response = provider.send_invoice_by_email(
                        provider_invoice_id=provider_result.provider_invoice_id,
                        email=customer.email,
                    )
                    _event(
                        db=db,
                        invoice_request_id=invoice_request.id,
                        event_type="email_sent",
                        payload={
                            "email_masked": _mask_email(customer.email),
                            "provider_invoice_id_present": bool(provider_result.provider_invoice_id),
                            "provider_ack": bool(email_response),
                        },
                    )
                except Exception as exc:
                    _event(
                        db=db,
                        invoice_request_id=invoice_request.id,
                        event_type="email_failed",
                        payload={
                            "email_masked": _mask_email(customer.email),
                        },
                        success=False,
                        error_message=str(exc)[:1000],
                    )
                    invoice_request.provider_last_error = str(exc)[:1000]
        else:
            invoice_request.status = InvoiceRequest.STATUS_PROCESSING
            _event(
                db=db,
                invoice_request_id=invoice_request.id,
                event_type="processing",
                payload={
                    "provider_invoice_id": provider_result.provider_invoice_id,
                },
            )

    # TODO(cleanup): Reemplazar excepción genérica por excepciones de dominio/integración para respuestas más precisas.
    except Exception as exc:
        invoice_request.attempts += 1
        invoice_request.status = InvoiceRequest.STATUS_FAILED
        invoice_request.provider_last_error = str(exc)[:1000]

        _event(
            db=db,
            invoice_request_id=invoice_request.id,
            event_type="failed",
            payload={"stage": "issue_invoice"},
            success=False,
            error_message=str(exc)[:1000],
        )

    db.commit()

    message = "Solicitud de factura procesada"
    if invoice_request.status == InvoiceRequest.STATUS_FAILED:
        message = "Solicitud creada pero fallo la emision. Revisa el estado para detalle"
    elif invoice_request.status == InvoiceRequest.STATUS_PROCESSING:
        message = "Solicitud creada y en procesamiento"

    return InvoiceEmitResponse(
        invoice_request_id=invoice_request.id,
        status=invoice_request.status,
        fiscal_customer_id=invoice_request.fiscal_customer_id,
        source_type=invoice_request.source_type,
        source_id=invoice_request.source_id,
        idempotency_key=invoice_request.idempotency_key,
        access_token=access_token,
        access_token_expires_at=access_token_expires_at,
        created_at=invoice_request.created_at,
        message=message,
    )


# TODO(refactor): Consolidar validación de token y carga de `invoice_request` en una dependencia reusable.
@router.get("/solicitudes/{invoice_request_id}", response_model=InvoiceRequestStatusResponse)
def obtener_estado_solicitud(
    invoice_request_id: int,
    access_token: str | None = Query(default=None, min_length=20, max_length=300),
    x_invoice_access_token: str | None = Header(default=None, alias="X-Invoice-Access-Token"),
    db: Session = Depends(get_db),
):
    invoice_request = db.query(InvoiceRequest).filter(InvoiceRequest.id == invoice_request_id).first()
    if not invoice_request:
        raise HTTPException(status_code=404, detail="Solicitud de factura no encontrada")

    token = _resolve_access_token(access_token, x_invoice_access_token)
    _authorize_invoice_access(invoice_request, token)

    doc = db.query(InvoiceDocument).filter(InvoiceDocument.invoice_request_id == invoice_request.id).first()

    return InvoiceRequestStatusResponse(
        invoice_request_id=invoice_request.id,
        status=invoice_request.status,
        fiscal_customer_id=invoice_request.fiscal_customer_id,
        issued_at=doc.issued_at if doc else None,
        total=doc.total if doc else invoice_request.total,
        currency=doc.currency if doc else invoice_request.currency,
        documents_ready=bool(invoice_request.provider_invoice_id and doc),
        can_cancel=invoice_request.status == InvoiceRequest.STATUS_ISSUED,
        attempts=invoice_request.attempts,
        created_at=invoice_request.created_at,
        updated_at=invoice_request.updated_at,
    )


@router.post("/solicitudes/{invoice_request_id}/cancelar", response_model=InvoiceCancelResponse)
def cancelar_factura(
    invoice_request_id: int,
    payload: InvoiceCancelRequest,
    access_token: str | None = Query(default=None, min_length=20, max_length=300),
    x_invoice_access_token: str | None = Header(default=None, alias="X-Invoice-Access-Token"),
    db: Session = Depends(get_db),
):
    invoice_request = db.query(InvoiceRequest).filter(InvoiceRequest.id == invoice_request_id).first()
    if not invoice_request:
        raise HTTPException(status_code=404, detail="Solicitud de factura no encontrada")

    token = _resolve_access_token(access_token, x_invoice_access_token)
    _authorize_invoice_access(invoice_request, token)

    if invoice_request.status != InvoiceRequest.STATUS_ISSUED:
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede cancelar una solicitud con status '{InvoiceRequest.STATUS_ISSUED}'",
        )

    if not invoice_request.provider_invoice_id:
        raise HTTPException(status_code=400, detail="La solicitud no tiene provider_invoice_id para cancelar")

    provider = get_invoice_provider(invoice_request.provider_name)
    cancel_result = provider.cancel_invoice(
        provider_invoice_id=invoice_request.provider_invoice_id,
        motivo=payload.motivo,
        comentario=payload.comentario,
    )

    invoice_request.status = InvoiceRequest.STATUS_CANCELLED

    doc = db.query(InvoiceDocument).filter(InvoiceDocument.invoice_request_id == invoice_request.id).first()
    cancelled_at = None
    if doc:
        doc.status = InvoiceDocument.STATUS_CANCELLED
        if cancel_result.cancelled_at:
            try:
                cancelled_at = datetime.fromisoformat(cancel_result.cancelled_at.replace("Z", "+00:00"))
            except Exception:
                cancelled_at = datetime.utcnow()
        else:
            cancelled_at = datetime.utcnow()
        doc.cancelled_at = cancelled_at

    _event(
        db=db,
        invoice_request_id=invoice_request.id,
        event_type="cancelled",
        payload={
            "motivo": payload.motivo,
            "provider_invoice_id": invoice_request.provider_invoice_id,
        },
    )

    db.commit()

    return InvoiceCancelResponse(
        invoice_request_id=invoice_request.id,
        status=invoice_request.status,
        cancelled_at=cancelled_at,
        message="Factura cancelada correctamente",
    )


# TODO(cleanup): Evitar duplicación entre endpoints XML/PDF extrayendo helper común para autorización y descarga.
@router.get("/solicitudes/{invoice_request_id}/xml")
def obtener_xml_factura(
    invoice_request_id: int,
    access_token: str | None = Query(default=None, min_length=20, max_length=300),
    x_invoice_access_token: str | None = Header(default=None, alias="X-Invoice-Access-Token"),
    db: Session = Depends(get_db),
):
    invoice_request = db.query(InvoiceRequest).filter(InvoiceRequest.id == invoice_request_id).first()
    if not invoice_request:
        raise HTTPException(status_code=404, detail="Solicitud de factura no encontrada")

    token = _resolve_access_token(access_token, x_invoice_access_token)
    _authorize_invoice_access(invoice_request, token)

    if not invoice_request.provider_invoice_id:
        raise HTTPException(status_code=400, detail="La solicitud no tiene factura asociada aun")

    provider = get_invoice_provider(invoice_request.provider_name)
    xml_bytes, content_type = provider.get_invoice_xml(invoice_request.provider_invoice_id)
    return Response(
        content=xml_bytes,
        media_type=content_type or "application/xml",
        headers={"Content-Disposition": f'attachment; filename="factura_{invoice_request_id}.xml"'},
    )


# TODO(cleanup): Evitar duplicación entre endpoints XML/PDF extrayendo helper común para autorización y descarga.
@router.get("/solicitudes/{invoice_request_id}/pdf")
def obtener_pdf_factura(
    invoice_request_id: int,
    access_token: str | None = Query(default=None, min_length=20, max_length=300),
    x_invoice_access_token: str | None = Header(default=None, alias="X-Invoice-Access-Token"),
    db: Session = Depends(get_db),
):
    invoice_request = db.query(InvoiceRequest).filter(InvoiceRequest.id == invoice_request_id).first()
    if not invoice_request:
        raise HTTPException(status_code=404, detail="Solicitud de factura no encontrada")

    token = _resolve_access_token(access_token, x_invoice_access_token)
    _authorize_invoice_access(invoice_request, token)

    if not invoice_request.provider_invoice_id:
        raise HTTPException(status_code=400, detail="La solicitud no tiene factura asociada aun")

    provider = get_invoice_provider(invoice_request.provider_name)
    pdf_bytes, content_type = provider.get_invoice_pdf(invoice_request.provider_invoice_id)
    return Response(
        content=pdf_bytes,
        media_type=content_type or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="factura_{invoice_request_id}.pdf"'},
    )
