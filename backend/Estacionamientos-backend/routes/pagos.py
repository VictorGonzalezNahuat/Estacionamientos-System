from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import os
from core.security import get_current_user
from core.payment_provider import get_payment_provider
from core.parking_exit_service import (
    cancelar_transaccion_pago,
    procesar_webhook_pago,
    registrar_salida_tarjeta_pendiente,
)
from database import get_db
from models.history_estacionamiento import HistoryEstacionamiento
from models.payment_transaction import PaymentTransaction
from models.usuario import Usuario
from schemas.payment_transaction import (
    CancelarPagoRequest,
    CancelarPagoResponse,
    SalirTarjetaRequest,
    SalirTarjetaResponse,
    PaymentTransactionResponse,
    PagoEstadoDetalleResponse,
)


router = APIRouter()


def _get_provider_name() -> str:
    return os.getenv("PAYMENT_PROVIDER", "stripe").strip().lower()


@router.post("/cancelar/{preferencia_id}", response_model=CancelarPagoResponse)
def cancelar_pago(
    preferencia_id: str,
    payload: CancelarPagoRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _ = current_user
    return CancelarPagoResponse(
        **cancelar_transaccion_pago(
            db=db,
            preferencia_id=preferencia_id,
            provider_name=payload.provider or _get_provider_name(),
            motivo=payload.motivo,
        )
    )


@router.post("/salir_tarjeta", response_model=SalirTarjetaResponse)
def salir_tarjeta(
    request: SalirTarjetaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resultado = registrar_salida_tarjeta_pendiente(
        db=db,
        current_user=current_user,
        placa=request.placa,
        provider_name=request.provider or _get_provider_name(),
        email=request.email,
    )
    return SalirTarjetaResponse(**resultado.to_dict())


@router.post("/webhook/stripe")
async def webhook_stripe(request: Request, db: Session = Depends(get_db)):
    return await _procesar_webhook(request, db, forced_provider="stripe")


@router.post("/webhook/mercadopago")
async def webhook_mercadopago(request: Request, db: Session = Depends(get_db)):
    return await _procesar_webhook(request, db, forced_provider="mercadopago")


@router.post("/webhook")
async def webhook_generico(request: Request, db: Session = Depends(get_db)):
    return await _procesar_webhook(request, db, forced_provider=None)


async def _procesar_webhook(request: Request, db: Session, forced_provider: str | None):
    """
    Webhook agnostico para Stripe o MercadoPago.
    """
    headers = dict(request.headers)

    if forced_provider:
        provider_name = forced_provider
    elif headers.get("Stripe-Signature") or headers.get("stripe-signature"):
        provider_name = "stripe"
    elif headers.get("X-Signature") or headers.get("x-signature"):
        provider_name = "mercadopago"
    else:
        provider_name = _get_provider_name()

    provider = get_payment_provider(provider_name)
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    if not provider.validate_webhook_signature(headers, body_str):
        raise HTTPException(status_code=403, detail="Firma de webhook inválida")

    parsed = provider.parse_webhook_event(body_str)
    return procesar_webhook_pago(db, provider, parsed)


@router.get("/estado/{preferencia_id}", response_model=PagoEstadoDetalleResponse)
def obtener_estado_pago_detalle(
    preferencia_id: str,
    db: Session = Depends(get_db)
):
    transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.preferencia_id == preferencia_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.payment_transaction_id == transaction.id
    ).order_by(desc(HistoryEstacionamiento.id)).first()

    estado_transaccion = transaction.estado
    pagado = bool(historial.pagado) if historial else False
    transaccion_exitosa = estado_transaccion == "completado" and pagado
    mensaje_estado = {
        "completado": "Pago confirmado",
        "pendiente": "Pago pendiente de confirmacion",
        "rechazado": "Pago rechazado",
        "cancelado": "Pago cancelado",
    }.get(estado_transaccion, "Estado de pago desconocido")

    return PagoEstadoDetalleResponse(
        preferencia_id=transaction.preferencia_id,
        payment_intent=transaction.payment_intent,
        placa=transaction.placa,
        estado_transaccion=estado_transaccion,
        transaccion_exitosa=transaccion_exitosa,
        mensaje_estado=mensaje_estado,
        pagado=pagado,
        metodo_pago=historial.metodo_pago if historial else None,
        importe=float(historial.importe) if historial else float(transaction.monto),
        webhook_timestamp=transaction.webhook_timestamp,
    )


@router.get("/pagos/{preferencia_id}", response_model=PaymentTransactionResponse)
def obtener_estado_pago_legacy(
    preferencia_id: str,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para consultar el estado de un pago (opcional, para polling).
    Útil si el cliente quiere verificar manualmente si su pago fue procesado.
    """
    
    transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.preferencia_id == preferencia_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    return PaymentTransactionResponse.from_orm(transaction)


@router.get("/placa/{placa}/pendiente", response_model=PagoEstadoDetalleResponse)
def obtener_pendiente_por_placa(
    placa: str,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    placa_norm = placa.strip().upper()
    transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.placa == placa_norm
    ).order_by(desc(PaymentTransaction.created_at)).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="No hay transacciones para la placa")

    historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.payment_transaction_id == transaction.id
    ).order_by(desc(HistoryEstacionamiento.id)).first()

    return PagoEstadoDetalleResponse(
        preferencia_id=transaction.preferencia_id,
        payment_intent=transaction.payment_intent,
        placa=transaction.placa,
        estado_transaccion=transaction.estado,
        transaccion_exitosa=transaction.estado == "completado" and (bool(historial.pagado) if historial else False),
        mensaje_estado={
            "completado": "Pago confirmado",
            "pendiente": "Pago pendiente de confirmacion",
            "rechazado": "Pago rechazado",
            "cancelado": "Pago cancelado",
        }.get(transaction.estado, "Estado de pago desconocido"),
        pagado=bool(historial.pagado) if historial else False,
        metodo_pago=historial.metodo_pago if historial else None,
        importe=float(historial.importe) if historial else float(transaction.monto),
        webhook_timestamp=transaction.webhook_timestamp,
    )
