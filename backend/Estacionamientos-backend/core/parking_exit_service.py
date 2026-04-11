from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from core.datetime_utils import now_local_naive
from core.payment_provider import ParsedWebhookEvent, get_payment_provider
from core.parking_pricing import calcular_importe_por_minutos, calcular_minutos_estadia
from core.parking_ticket_service import (
    construir_ticket_salida,
    guardar_ticket_bytes,
    imprimir_lote_tickets_salida,
)
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.invoice_request import InvoiceRequest
from models.payment_transaction import PaymentTransaction
from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.ticket_cancelado import TicketCancelado
from models.turno import Turno
from models.usuario import Usuario


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParkingExitContext:
    placa: str
    salida_dt: datetime
    fecha_salida: date
    hora_salida: time
    fecha_entrada: date
    hora_entrada: time
    total_minutos: int
    importe: float
    tarifa_id: int
    turno_id: int
    encargado_id: int
    cajero_nombre: str
    metodo_pago: str
    proveedor_pago: Optional[str] = None
    email: Optional[str] = None

    def to_metadata(self) -> dict:
        return {
            "placa": self.placa,
            "salida_dt": self.salida_dt.isoformat(),
            "fecha_salida": self.fecha_salida.isoformat(),
            "hora_salida": self.hora_salida.isoformat(),
            "fecha_entrada": self.fecha_entrada.isoformat(),
            "hora_entrada": self.hora_entrada.isoformat(),
            "total_minutos": self.total_minutos,
            "importe": float(self.importe),
            "tarifa_id": self.tarifa_id,
            "turno_id": self.turno_id,
            "encargado_id": self.encargado_id,
            "cajero_nombre": self.cajero_nombre,
            "metodo_pago": self.metodo_pago,
            "proveedor_pago": self.proveedor_pago,
            "email": self.email,
        }


@dataclass(frozen=True)
class ParkingExitResult:
    mensaje: str
    placa: str = ""
    monto: float = 0.0
    fecha_salida: str = ""
    hora_salida: str = ""
    minutos_estadia: int = 0
    estado: str = "pendiente"
    ticket_bin: str = ""
    ticket_impreso: bool = False
    impresion_mensaje: str = ""
    ticket_copias: int = 0
    preferencia_id: str = ""
    checkout_url: str = ""
    provider: str = ""
    payment_transaction_id: int | None = None
    history_estacionamiento_id: int | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        # Retrocompatibilidad: el frontend historicamente usa "importe".
        data["importe"] = data.get("monto", 0.0)
        return data


def _metadata_from_transaction(payment_transaction: PaymentTransaction) -> dict:
    return payment_transaction.metadata_as_dict()


def _obtener_turno_activo(db: Session, current_user: Usuario) -> Turno:
    turno = db.query(Turno).filter(Turno.encargado_id == current_user.id, Turno.estado == "activo").first()
    if not turno:
        raise HTTPException(status_code=404, detail="No existe turno abierto para el usuario actual")
    return turno


def _obtener_vehiculo(db: Session, placa: str) -> CurrentEstacionamiento:
    vehiculo = db.query(CurrentEstacionamiento).filter(CurrentEstacionamiento.placa == placa).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    return vehiculo


def _obtener_tarifa(db: Session, tarifa_id: int) -> Tarifa:
    tarifa = db.query(Tarifa).filter(Tarifa.id == tarifa_id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return tarifa


def _resolver_nombre_cajero(db: Session, historial: HistoryEstacionamiento) -> str:
    encargado_nombre = "SISTEMA"

    turno_historial = db.query(Turno).filter(Turno.id == historial.turno_id).first()
    if turno_historial:
        encargado_turno = db.query(Usuario).filter(Usuario.id == turno_historial.encargado_id).first()
        if encargado_turno and getattr(encargado_turno, "nombre", None):
            encargado_nombre = encargado_turno.nombre

    if encargado_nombre == "SISTEMA":
        encargado_historial = db.query(Usuario).filter(Usuario.id == historial.encargado_id).first()
        if encargado_historial and getattr(encargado_historial, "nombre", None):
            encargado_nombre = encargado_historial.nombre

    return encargado_nombre or "SISTEMA"


def _crear_contexto_salida(db: Session, current_user: Usuario, placa: str, metodo_pago: str = "efectivo") -> ParkingExitContext:
    placa_norm = placa.strip().upper()
    vehiculo = _obtener_vehiculo(db, placa_norm)
    tarifa = _obtener_tarifa(db, vehiculo.tarifa_id)
    turno_usuario = _obtener_turno_activo(db, current_user)

    salida_dt = now_local_naive()
    total_minutos = calcular_minutos_estadia(vehiculo.fecha_entrada, vehiculo.hora_entrada, salida_dt)
    importe = calcular_importe_por_minutos(total_minutos, tarifa)

    return ParkingExitContext(
        placa=placa_norm,
        salida_dt=salida_dt,
        fecha_salida=salida_dt.date(),
        hora_salida=salida_dt.time(),
        fecha_entrada=vehiculo.fecha_entrada,
        hora_entrada=vehiculo.hora_entrada,
        total_minutos=total_minutos,
        importe=importe,
        tarifa_id=vehiculo.tarifa_id,
        turno_id=turno_usuario.id,
        encargado_id=vehiculo.encargado_id,
        cajero_nombre=getattr(current_user, "nombre", "SISTEMA"),
        metodo_pago=metodo_pago,
    )


def _crear_historial(db: Session, context: ParkingExitContext, payment_transaction_id: int | None, pagado: bool) -> HistoryEstacionamiento:
    historial = HistoryEstacionamiento(
        tarifa_id=context.tarifa_id,
        encargado_id=context.encargado_id,
        turno_id=context.turno_id,
        fecha_entrada=context.fecha_entrada,
        hora_entrada=context.hora_entrada,
        fecha_salida=context.fecha_salida,
        hora_salida=context.hora_salida,
        placa=context.placa,
        importe=context.importe,
        metodo_pago=context.metodo_pago,
        pagado=pagado,
        payment_transaction_id=payment_transaction_id,
    )
    db.add(historial)
    db.flush()
    return historial


def _cerrar_vehiculo(db: Session, placa: str) -> None:
    vehiculo = db.query(CurrentEstacionamiento).filter(CurrentEstacionamiento.placa == placa).first()
    if vehiculo:
        estado = db.query(StateEstacionamiento).first()
        if estado:
            estado.espacios_ocupados = max(0, estado.espacios_ocupados - 1)
        db.delete(vehiculo)


def _construir_ticket_salida_historial(
    historial: HistoryEstacionamiento,
    cajero_nombre: str,
    etiqueta: str,
    leyenda_reimpresion: str | None = None,
) -> bytes:
    entrada = datetime.combine(historial.fecha_entrada, historial.hora_entrada)
    salida_historial_dt = datetime.combine(historial.fecha_salida, historial.hora_salida)
    minutos_estadia = max(1, int((salida_historial_dt - entrada).total_seconds() / 60))
    folio_salida = str(historial.id)

    return construir_ticket_salida(
        folio=folio_salida,
        placa=historial.placa,
        fecha_entrada=entrada,
        fecha_salida=salida_historial_dt,
        minutos_estadia=minutos_estadia,
        total_pagado=float(historial.importe),
        cajero=cajero_nombre,
        metodo_pago="En linea" if historial.metodo_pago == "tarjeta" else "Efectivo",
        etiqueta=etiqueta,
        leyenda_reimpresion=leyenda_reimpresion,
    )


def reimprimir_ticket_salida_desde_historial(
    db: Session,
    historial: HistoryEstacionamiento,
    leyenda_reimpresion: str | None = None,
) -> tuple[bool, str, int]:
    cajero_nombre = _resolver_nombre_cajero(db, historial)
    ticket_bytes = _construir_ticket_salida_historial(
        historial,
        cajero_nombre,
        "ORIGINAL",
        leyenda_reimpresion=leyenda_reimpresion,
    )
    ticket_copia_bytes = _construir_ticket_salida_historial(
        historial,
        cajero_nombre,
        "COPIA",
        leyenda_reimpresion=leyenda_reimpresion,
    )
    impreso_ok, impresion_mensaje = imprimir_lote_tickets_salida([ticket_bytes, ticket_copia_bytes])
    return impreso_ok, impresion_mensaje, 2


def registrar_salida_efectivo(db: Session, current_user: Usuario, placa: str) -> ParkingExitResult:
    context = _crear_contexto_salida(db, current_user, placa, metodo_pago="efectivo")

    historial = _crear_historial(db, context, payment_transaction_id=None, pagado=True)
    _cerrar_vehiculo(db, context.placa)
    db.commit()

    folio = str(historial.id)
    ticket_bytes = construir_ticket_salida(
        folio=folio,
        placa=context.placa,
        fecha_entrada=datetime.combine(context.fecha_entrada, context.hora_entrada),
        fecha_salida=context.salida_dt,
        minutos_estadia=context.total_minutos,
        total_pagado=float(context.importe),
        cajero=context.cajero_nombre,
        metodo_pago="Efectivo",
        etiqueta="ORIGINAL",
    )
    ticket_copia_bytes = construir_ticket_salida(
        folio=folio,
        placa=context.placa,
        fecha_entrada=datetime.combine(context.fecha_entrada, context.hora_entrada),
        fecha_salida=context.salida_dt,
        minutos_estadia=context.total_minutos,
        total_pagado=float(context.importe),
        cajero=context.cajero_nombre,
        metodo_pago="Efectivo",
        etiqueta="COPIA",
    )
    ticket_path = guardar_ticket_bytes("salida", context.placa, context.salida_dt, ticket_bytes)
    impreso_ok, impresion_mensaje = imprimir_lote_tickets_salida([ticket_bytes, ticket_copia_bytes])

    return ParkingExitResult(
        mensaje="Vehiculo retirado correctamente",
        placa=context.placa,
        monto=float(context.importe),
        fecha_salida=str(context.fecha_salida),
        hora_salida=str(context.hora_salida),
        minutos_estadia=context.total_minutos,
        estado="completado",
        ticket_bin=str(ticket_path),
        ticket_impreso=impreso_ok,
        impresion_mensaje=impresion_mensaje,
        ticket_copias=2,
        history_estacionamiento_id=historial.id,
    )


def _resolver_salida_tarjeta_pendiente_existente(
    db: Session,
    context: ParkingExitContext,
    selected_provider: str,
) -> ParkingExitResult | None:
    tx_pendiente = db.query(PaymentTransaction).filter(
        PaymentTransaction.placa == context.placa,
        PaymentTransaction.estado == PaymentTransaction.ESTADO_PENDIENTE,
    ).order_by(desc(PaymentTransaction.created_at)).first()

    if not tx_pendiente:
        return None

    metadata_existente = _metadata_from_transaction(tx_pendiente)
    checkout_existente = metadata_existente.get("checkout_url")
    provider_existente = metadata_existente.get("provider", selected_provider)

    historial_pendiente = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.payment_transaction_id == tx_pendiente.id,
        HistoryEstacionamiento.pagado == False,
    ).first()

    if not checkout_existente or not historial_pendiente:
        return None

    return ParkingExitResult(
        mensaje="Ya existe una salida pendiente de pago para esta placa.",
        preferencia_id=tx_pendiente.preferencia_id,
        checkout_url=checkout_existente,
        provider=provider_existente,
        placa=tx_pendiente.placa,
        monto=float(tx_pendiente.monto),
        fecha_salida=str(historial_pendiente.fecha_salida),
        hora_salida=str(historial_pendiente.hora_salida),
        minutos_estadia=context.total_minutos,
        estado="pendiente",
        history_estacionamiento_id=historial_pendiente.id,
    )


def _crear_checkout_tarjeta(
    context: ParkingExitContext,
    selected_provider: str,
    email: str | None,
) -> tuple[str, str]:
    try:
        preferencia_id, checkout_url = get_payment_provider(selected_provider).create_checkout(
            placa=context.placa,
            monto=context.importe,
            email=email,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al crear checkout: {str(exc)}") from exc

    return preferencia_id, checkout_url


def _persistir_salida_tarjeta_pendiente(
    db: Session,
    context: ParkingExitContext,
    selected_provider: str,
    preferencia_id: str,
    checkout_url: str,
) -> tuple[PaymentTransaction, HistoryEstacionamiento]:
    metadata_mp = PaymentTransaction.build_metadata(
        {
            PaymentTransaction.METADATA_PROVIDER_KEY: selected_provider,
            PaymentTransaction.METADATA_CHECKOUT_URL_KEY: checkout_url,
            PaymentTransaction.METADATA_CREATED_AT_KEY: context.salida_dt.isoformat(),
            PaymentTransaction.METADATA_EXIT_CONTEXT_KEY: context.to_metadata(),
        }
    )
    payment_transaction = PaymentTransaction(
        preferencia_id=preferencia_id,
        placa=context.placa,
        monto=context.importe,
        estado=PaymentTransaction.ESTADO_PENDIENTE,
        metadata_mp=metadata_mp,
    )
    db.add(payment_transaction)
    db.flush()

    historial = _crear_historial(db, context, payment_transaction_id=payment_transaction.id, pagado=False)
    db.commit()
    return payment_transaction, historial


def _generar_ticket_salida_pendiente(context: ParkingExitContext, historial: HistoryEstacionamiento) -> str:
    folio = str(historial.id)
    ticket_bytes = construir_ticket_salida(
        folio=folio,
        placa=context.placa,
        fecha_entrada=datetime.combine(context.fecha_entrada, context.hora_entrada),
        fecha_salida=context.salida_dt,
        minutos_estadia=context.total_minutos,
        total_pagado=float(context.importe),
        cajero=context.cajero_nombre,
        metodo_pago="Tarjeta",
        etiqueta="ORIGINAL",
    )
    ticket_path = guardar_ticket_bytes("salida", context.placa, context.salida_dt, ticket_bytes, suffix="_pendiente")
    return str(ticket_path)

def registrar_salida_tarjeta_pendiente(
    db: Session,
    current_user: Usuario,
    placa: str,
    provider_name: str,
    email: str | None = None,
) -> ParkingExitResult:
    context = _crear_contexto_salida(db, current_user, placa, metodo_pago="tarjeta")
    selected_provider = (provider_name or "stripe").strip().lower()

    pendiente_existente = _resolver_salida_tarjeta_pendiente_existente(
        db=db,
        context=context,
        selected_provider=selected_provider,
    )
    if pendiente_existente:
        return pendiente_existente

    preferencia_id, checkout_url = _crear_checkout_tarjeta(
        context=context,
        selected_provider=selected_provider,
        email=email,
    )

    payment_transaction, historial = _persistir_salida_tarjeta_pendiente(
        db=db,
        context=context,
        selected_provider=selected_provider,
        preferencia_id=preferencia_id,
        checkout_url=checkout_url,
    )

    ticket_path = _generar_ticket_salida_pendiente(context=context, historial=historial)

    return ParkingExitResult(
        mensaje="Salida registrada. Pendiente pago por tarjeta. Completa el pago para finalizar.",
        preferencia_id=preferencia_id,
        checkout_url=checkout_url,
        provider=selected_provider,
        placa=context.placa,
        monto=float(context.importe),
        fecha_salida=str(context.fecha_salida),
        hora_salida=str(context.hora_salida),
        minutos_estadia=context.total_minutos,
        ticket_bin=ticket_path,
        estado="pendiente",
        payment_transaction_id=payment_transaction.id,
        history_estacionamiento_id=historial.id,
    )


def _buscar_transaccion_por_lookup(db: Session, parsed: ParsedWebhookEvent) -> PaymentTransaction | None:
    if parsed.lookup_field == "preferencia_id":
        return db.query(PaymentTransaction).filter(
            PaymentTransaction.preferencia_id == parsed.lookup_value
        ).first()

    if parsed.lookup_field == "placa":
        payment_transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.placa == parsed.lookup_value,
            PaymentTransaction.estado == PaymentTransaction.ESTADO_PENDIENTE,
        ).order_by(desc(PaymentTransaction.created_at)).first()

        if payment_transaction:
            return payment_transaction

        return db.query(PaymentTransaction).filter(
            PaymentTransaction.placa == parsed.lookup_value
        ).order_by(desc(PaymentTransaction.created_at)).first()

    raise HTTPException(status_code=400, detail="lookup_field no soportado")


def _actualizar_metadata_webhook(payment_transaction: PaymentTransaction, provider, parsed: ParsedWebhookEvent) -> None:
    payment_transaction.webhook_timestamp = datetime.utcnow()
    existing_metadata = _metadata_from_transaction(payment_transaction)
    merged_metadata = {
        **existing_metadata,
        PaymentTransaction.METADATA_PROVIDER_EVENT_KEY: parsed.event_payload or {},
    }
    payment_transaction.metadata_mp = provider.serialize_event(merged_metadata)


def _resolver_accion_transicion(estado_actual: str, normalized_status: str | None) -> str:
    if estado_actual == PaymentTransaction.ESTADO_CANCELADO:
        return "ignored_cancelled"

    if normalized_status == "completado":
        if estado_actual == PaymentTransaction.ESTADO_COMPLETADO:
            return "processed_already"
        return "mark_completed"

    if normalized_status == "rechazado":
        if estado_actual == PaymentTransaction.ESTADO_COMPLETADO:
            return "keep_current"
        return "mark_rejected"

    if normalized_status == "cancelado":
        if estado_actual == PaymentTransaction.ESTADO_COMPLETADO:
            return "keep_current"
        return "mark_cancelled"

    if estado_actual == PaymentTransaction.ESTADO_COMPLETADO:
        return "keep_current"
    return "mark_pending"


def _aplicar_transicion_estado(payment_transaction: PaymentTransaction, parsed: ParsedWebhookEvent, accion: str) -> None:
    if accion in {"processed_already", "mark_completed"}:
        if parsed.provider_transaction_id and not payment_transaction.payment_intent:
            payment_transaction.payment_intent = parsed.provider_transaction_id

    if accion == "mark_completed":
        payment_transaction.estado = PaymentTransaction.ESTADO_COMPLETADO
    elif accion == "mark_rejected":
        payment_transaction.estado = PaymentTransaction.ESTADO_RECHAZADO
    elif accion == "mark_cancelled":
        payment_transaction.estado = PaymentTransaction.ESTADO_CANCELADO
    elif accion == "mark_pending":
        payment_transaction.estado = PaymentTransaction.ESTADO_PENDIENTE


def _clasificar_error_impresion(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, TimeoutError):
        return "transitorio", "timeout al imprimir"

    if isinstance(exc, (ConnectionError, OSError)):
        return "transitorio", "fallo de conectividad con impresora"

    if isinstance(exc, (ValueError, TypeError)):
        return "permanente", "configuracion o datos invalidos para impresion"

    return "desconocido", "error no clasificado de impresion"


def _reportar_error_impresion(exc: Exception) -> None:
    categoria, causa = _clasificar_error_impresion(exc)
    print(f"Error imprimiendo ticket [{categoria}] {causa}: {exc}")


def _finalizar_salida_pagada_tarjeta(db: Session, historial: HistoryEstacionamiento) -> None:
    if int(getattr(historial, "cancelado", 0)) == 1:
        return

    historial.pagado = True
    _cerrar_vehiculo(db, historial.placa)

    try:
        cajero_nombre = _resolver_nombre_cajero(db, historial)
        ticket_bytes = _construir_ticket_salida_historial(historial, cajero_nombre, "ORIGINAL")
        ticket_copia_bytes = _construir_ticket_salida_historial(historial, cajero_nombre, "COPIA")

        impreso_ok, impresion_mensaje = imprimir_lote_tickets_salida([ticket_bytes, ticket_copia_bytes])
        if not impreso_ok:
            print(f"Advertencia impresion salida tarjeta | {impresion_mensaje}")
    except TimeoutError as exc:
        _reportar_error_impresion(exc)
    except (ConnectionError, OSError) as exc:
        _reportar_error_impresion(exc)
    except (ValueError, TypeError) as exc:
        _reportar_error_impresion(exc)
    except Exception as exc:
        _reportar_error_impresion(exc)


def _respuesta_webhook(status: str, provider, parsed: ParsedWebhookEvent, payment_transaction: PaymentTransaction) -> dict:
    return {
        "status": status,
        "provider": provider.provider_name,
        "lookup_field": parsed.lookup_field,
        "lookup_value": parsed.lookup_value,
        "transaction_status": payment_transaction.estado,
    }


def procesar_webhook_pago(db: Session, provider, parsed: ParsedWebhookEvent) -> dict:
    if not parsed.should_process:
        return {"status": "ignored"}

    if not parsed.lookup_field or not parsed.lookup_value:
        raise HTTPException(status_code=400, detail="Evento sin referencia para buscar transaccion")

    payment_transaction = _buscar_transaccion_por_lookup(db=db, parsed=parsed)

    if not payment_transaction:
        logger.warning(
            "webhook_not_found provider=%s lookup_field=%s lookup_value=%s",
            getattr(provider, "provider_name", "unknown"),
            parsed.lookup_field,
            parsed.lookup_value,
        )
        return {"status": "not_found"}

    _actualizar_metadata_webhook(payment_transaction=payment_transaction, provider=provider, parsed=parsed)

    historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.placa == payment_transaction.placa,
        HistoryEstacionamiento.payment_transaction_id == payment_transaction.id,
    ).first()

    if historial and int(getattr(historial, "cancelado", 0)) == 1:
        payment_transaction.estado = PaymentTransaction.ESTADO_CANCELADO
        db.commit()
        return _respuesta_webhook(
            status="ignored_cancelled_ticket",
            provider=provider,
            parsed=parsed,
            payment_transaction=payment_transaction,
        )

    accion = _resolver_accion_transicion(
        estado_actual=payment_transaction.estado,
        normalized_status=parsed.normalized_status,
    )

    if accion == "ignored_cancelled":
        db.commit()
        return _respuesta_webhook(
            status="ignored_cancelled",
            provider=provider,
            parsed=parsed,
            payment_transaction=payment_transaction,
        )

    _aplicar_transicion_estado(payment_transaction=payment_transaction, parsed=parsed, accion=accion)

    if accion == "processed_already":
        db.commit()
        return _respuesta_webhook(
            status="processed_already",
            provider=provider,
            parsed=parsed,
            payment_transaction=payment_transaction,
        )

    if accion == "mark_completed" and historial:
        _finalizar_salida_pagada_tarjeta(db=db, historial=historial)

    db.commit()

    return _respuesta_webhook(
        status="processed",
        provider=provider,
        parsed=parsed,
        payment_transaction=payment_transaction,
    )


def _motivo_cancelacion_normalizado(motivo: str | None) -> str:
    motivo_limpio = (motivo or "").strip()
    if not motivo_limpio:
        raise HTTPException(status_code=400, detail="El motivo de cancelacion es obligatorio")
    if len(motivo_limpio) > 500:
        raise HTTPException(status_code=400, detail="El motivo de cancelacion no puede exceder 500 caracteres")
    return motivo_limpio


def _existe_factura_emitida_o_en_proceso(db: Session, history_id: int) -> bool:
    invoice_request = (
        db.query(InvoiceRequest)
        .filter(
            InvoiceRequest.source_type == InvoiceRequest.SOURCE_HISTORY_EXIT,
            InvoiceRequest.source_id == str(history_id),
            InvoiceRequest.status.in_([InvoiceRequest.STATUS_PROCESSING, InvoiceRequest.STATUS_ISSUED]),
        )
        .first()
    )
    return bool(invoice_request)


def _registrar_cancelacion_historial(
    db: Session,
    historial: HistoryEstacionamiento,
    payment_transaction: PaymentTransaction | None,
    cancelado_por: int,
    motivo: str,
) -> None:
    historial.cancelado = 1

    registro_cancelacion = TicketCancelado(
        history_estacionamiento_id=historial.id,
        payment_transaction_id=payment_transaction.id if payment_transaction else None,
        motivo=motivo,
        cancelado_por=cancelado_por,
        fecha_cancelacion=datetime.utcnow(),
    )
    db.add(registro_cancelacion)


def _resolver_provider_desde_transaccion(payment_transaction: PaymentTransaction, provider_name: str | None) -> str:
    if provider_name and provider_name.strip():
        return provider_name.strip().lower()

    metadata = _metadata_from_transaction(payment_transaction)
    provider_metadata = str(metadata.get(PaymentTransaction.METADATA_PROVIDER_KEY, "")).strip().lower()
    return provider_metadata or "stripe"


def cancelar_ticket_por_historial(
    db: Session,
    historial_id: int,
    current_user_id: int,
    motivo: str,
    provider_name: str | None = None,
) -> dict:
    motivo_limpio = _motivo_cancelacion_normalizado(motivo)

    historial = db.query(HistoryEstacionamiento).filter(HistoryEstacionamiento.id == historial_id).first()
    if not historial:
        raise HTTPException(status_code=404, detail="Registro historico no encontrado")

    if int(getattr(historial, "cancelado", 0)) == 1:
        raise HTTPException(status_code=409, detail="El ticket ya esta cancelado")

    if historial.corte_id is not None:
        raise HTTPException(status_code=409, detail="No se puede cancelar un ticket con corte asignado")

    if _existe_factura_emitida_o_en_proceso(db=db, history_id=historial.id):
        raise HTTPException(status_code=409, detail="No se puede cancelar un ticket ya facturado o en proceso de facturacion")

    payment_transaction = None
    cancelado_remoto = False
    detalle_cancelacion = "Cancelacion local exitosa"
    provider_normalized = provider_name.strip().lower() if provider_name else None

    if historial.payment_transaction_id is not None:
        payment_transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.id == historial.payment_transaction_id
        ).first()

        if payment_transaction:
            provider_normalized = _resolver_provider_desde_transaccion(payment_transaction, provider_normalized)
            provider = get_payment_provider(provider_normalized)
            provider_normalized = getattr(provider, "provider_name", provider_normalized)

            if payment_transaction.estado != PaymentTransaction.ESTADO_CANCELADO:
                try:
                    remote_result = provider.cancel_checkout(payment_transaction.preferencia_id)
                    cancelado_remoto = bool(remote_result.get("cancelled_remote", False))
                    detalle_cancelacion = remote_result.get("message") or detalle_cancelacion
                except Exception as exc:
                    detalle_cancelacion = f"No se pudo cancelar remoto: {str(exc)}"

            payment_transaction.estado = PaymentTransaction.ESTADO_CANCELADO
            metadata = {
                **_metadata_from_transaction(payment_transaction),
                "cancelled_remote": cancelado_remoto,
                "cancel_provider": provider_normalized,
                "cancel_reason": motivo_limpio,
                "cancel_detail": detalle_cancelacion,
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancelled_by_user_id": current_user_id,
                "cancelled_history_id": historial.id,
            }
            payment_transaction.metadata_mp = PaymentTransaction.build_metadata(metadata)

    _registrar_cancelacion_historial(
        db=db,
        historial=historial,
        payment_transaction=payment_transaction,
        cancelado_por=current_user_id,
        motivo=motivo_limpio,
    )
    db.commit()

    preferencia_id = payment_transaction.preferencia_id if payment_transaction else None
    return {
        "preferencia_id": preferencia_id,
        "estado_transaccion": payment_transaction.estado if payment_transaction else "sin_transaccion",
        "cancelado_local": True,
        "cancelado_remoto": cancelado_remoto,
        "provider": provider_normalized,
        "motivo": motivo_limpio,
        "detalle": detalle_cancelacion,
        "history_estacionamiento_id": historial.id,
    }


def cancelar_transaccion_pago(
    db: Session,
    preferencia_id: str,
    provider_name: str,
    current_user_id: int,
    motivo: str,
) -> dict:
    payment_transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.preferencia_id == preferencia_id
    ).first()

    if not payment_transaction:
        raise HTTPException(status_code=404, detail="Transaccion no encontrada")
    historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.payment_transaction_id == payment_transaction.id
    ).order_by(desc(HistoryEstacionamiento.id)).first()

    if not historial:
        raise HTTPException(status_code=404, detail="No existe ticket historico asociado a la transaccion")

    return cancelar_ticket_por_historial(
        db=db,
        historial_id=historial.id,
        current_user_id=current_user_id,
        motivo=motivo,
        provider_name=provider_name,
    )