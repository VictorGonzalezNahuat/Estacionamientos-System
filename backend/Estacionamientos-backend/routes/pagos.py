from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
import os
from core.security import get_current_user
from core.payment_provider import get_payment_provider
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.payment_transaction import PaymentTransaction
from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario
from printer.print import generar_ticket_salida_prueba, imprimir_ticket_red
from schemas.payment_transaction import SalirTarjetaRequest, SalirTarjetaResponse, PaymentTransactionResponse


router = APIRouter()


def _get_provider_name() -> str:
    return os.getenv("PAYMENT_PROVIDER", "stripe").strip().lower()


def _calcular_importe_por_minutos(total_minutos: int, tarifa: Tarifa):
    """Reutilizamos la función del módulo current_estacionamientos"""
    importe = 0
    minutos_restantes = total_minutos

    MINUTOS_DIA = 1440
    MINUTOS_MEDIO_DIA = 720
    MINUTOS_HORA = 60
    MINUTOS_FRACCION = 30

    dias = minutos_restantes // MINUTOS_DIA
    if dias > 0:
        importe += dias * tarifa.diario
        minutos_restantes = minutos_restantes % MINUTOS_DIA

    medios_dias = minutos_restantes // MINUTOS_MEDIO_DIA
    if medios_dias > 0:
        importe += medios_dias * tarifa.medio_dia
        minutos_restantes = minutos_restantes % MINUTOS_MEDIO_DIA

    if minutos_restantes > 0:
        if minutos_restantes <= MINUTOS_HORA:
            importe += tarifa.hora
            minutos_restantes = 0
        else:
            importe += tarifa.hora
            minutos_restantes -= MINUTOS_HORA

            horas_completas = minutos_restantes // MINUTOS_HORA
            importe += horas_completas * tarifa.hora
            minutos_restantes = minutos_restantes % MINUTOS_HORA

            if minutos_restantes == 0:
                pass
            elif minutos_restantes <= MINUTOS_FRACCION:
                importe += tarifa.fraccion
            else:
                importe += tarifa.hora

    return importe


def _calcular_minutos_estadia(fecha_entrada, hora_entrada, referencia_dt: datetime) -> int:
    """Reutilizamos la función del módulo current_estacionamientos"""
    from datetime import datetime as dt
    entrada = dt.combine(fecha_entrada, hora_entrada)
    tiempo_total = referencia_dt - entrada
    total_segundos = tiempo_total.total_seconds()

    if total_segundos < 0:
        raise ValueError("Tiempo invalido")

    return max(1, int(total_segundos / 60))


@router.post("/salir_tarjeta", response_model=SalirTarjetaResponse)
def salir_tarjeta(
    request: SalirTarjetaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para completar la salida de un vehículo utilizando pago por tarjeta.
    
    Flujo:
    1. Valida que el vehículo exista en current_estacionamiento
    2. Calcula el importe a pagar
    3. Crea checkout en el proveedor de pago configurado
    4. Registra la salida en history_estacionamiento (sin marcar como pagado aún)
    5. Retorna URL de checkout para completar el cobro
    
    El vehículo se mantiene en current_estacionamiento hasta confirmar el pago via webhook.
    """
    
    placa = request.placa.strip().upper()

    # 1. Validar que el vehículo existe
    vehiculo = db.query(CurrentEstacionamiento).filter(
        CurrentEstacionamiento.placa == placa
    ).first()

    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    # 2. Obtener tarifa
    tarifa = db.query(Tarifa).filter(Tarifa.id == vehiculo.tarifa_id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")

    # 3. Calcular importe
    salida_dt = datetime.now()
    fecha_salida = salida_dt.date()
    hora_salida = salida_dt.time()

    try:
        total_minutos = _calcular_minutos_estadia(
            vehiculo.fecha_entrada,
            vehiculo.hora_entrada,
            salida_dt
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Tiempo inválido")

    importe = _calcular_importe_por_minutos(total_minutos, tarifa)

    # 4. Crear checkout en el proveedor configurado
    selected_provider = request.provider or _get_provider_name()

    try:
        preferencia_id, checkout_url = get_payment_provider(selected_provider).create_checkout(
            placa=placa,
            monto=importe,
            email=request.email
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear checkout: {str(e)}")

    # 5. Guardar transacción de pago en BD (estado: pendiente)
    payment_transaction = PaymentTransaction(
        preferencia_id=preferencia_id,
        placa=placa,
        monto=importe,
        estado="pendiente"
    )
    db.add(payment_transaction)
    db.flush()  # Para obtener el ID sin hacer commit aún
    payment_transaction_id = payment_transaction.id

    # 6. Guardar salida en historial (sin marcar como pagado)
    turno_usuario = db.query(Turno).filter(
        Turno.encargado_id == current_user.id,
        Turno.estado == "activo"
    ).first()

    if not turno_usuario:
        raise HTTPException(status_code=404, detail="No existe turno abierto para el usuario actual")

    historial = HistoryEstacionamiento(
        tarifa_id=vehiculo.tarifa_id,
        encargado_id=vehiculo.encargado_id,
        turno_id=turno_usuario.id,
        fecha_entrada=vehiculo.fecha_entrada,
        hora_entrada=vehiculo.hora_entrada,
        fecha_salida=fecha_salida,
        hora_salida=hora_salida,
        placa=vehiculo.placa,
        importe=importe,
        metodo_pago="tarjeta",
        pagado=False,  # Pendiente de confirmación via webhook
        payment_transaction_id=payment_transaction_id
    )
    db.add(historial)
    db.commit()

    # 7. Generar ticket de salida (para referencia, sin imprimir aún)
    entrada = datetime.combine(vehiculo.fecha_entrada, vehiculo.hora_entrada)
    ticket_bytes = generar_ticket_salida_prueba(
        folio=f"SAL-{placa}-{salida_dt:%Y%m%d%H%M%S}",
        placa=placa,
        fecha_entrada=entrada,
        fecha_salida=salida_dt,
        minutos_estadia=total_minutos,
        total_pagado=float(importe),
        cajero=getattr(current_user, "nombre", "SISTEMA"),
        etiqueta="ORIGINAL"
    )

    tickets_dir = Path("printer") / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_dir / f"salida_{placa}_{salida_dt:%Y%m%d_%H%M%S}_pendiente.bin"
    ticket_path.write_bytes(ticket_bytes)

    return SalirTarjetaResponse(
        mensaje="Salida registrada. Pendiente pago por tarjeta. Completa el pago para finalizar.",
        preferencia_id=preferencia_id,
        checkout_url=checkout_url,
        placa=placa,
        monto=importe,
        fecha_salida=str(fecha_salida),
        hora_salida=str(hora_salida),
        minutos_estadia=total_minutos,
        ticket_bin=str(ticket_path)
    )


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
    if not parsed.should_process:
        return {"status": "ignored"}

    if not parsed.lookup_field or not parsed.lookup_value:
        raise HTTPException(status_code=400, detail="Evento sin referencia para buscar transaccion")

    if parsed.lookup_field == "preferencia_id":
        payment_transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.preferencia_id == parsed.lookup_value
        ).first()
    elif parsed.lookup_field == "placa":
        payment_transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.placa == parsed.lookup_value
        ).order_by(desc(PaymentTransaction.created_at)).first()
    else:
        raise HTTPException(status_code=400, detail="lookup_field no soportado")

    if not payment_transaction:
        print(f"No se encontro transaccion para {parsed.lookup_field}: {parsed.lookup_value}")
        return {"status": "not_found"}

    payment_transaction.webhook_timestamp = datetime.utcnow()
    payment_transaction.metadata_mp = provider.serialize_event(parsed.event_payload or {})
    placa = payment_transaction.placa

    if parsed.normalized_status == "completado":
        payment_transaction.estado = "completado"

        historial = db.query(HistoryEstacionamiento).filter(
            HistoryEstacionamiento.placa == placa,
            HistoryEstacionamiento.payment_transaction_id == payment_transaction.id
        ).first()

        if historial:
            historial.pagado = True

            vehiculo = db.query(CurrentEstacionamiento).filter(
                CurrentEstacionamiento.placa == placa
            ).first()

            if vehiculo:
                estado = db.query(StateEstacionamiento).first()
                if estado:
                    estado.espacios_ocupados = max(0, estado.espacios_ocupados - 1)
                db.delete(vehiculo)

            try:
                entrada = datetime.combine(historial.fecha_entrada, historial.hora_entrada)
                ticket_bytes = generar_ticket_salida_prueba(
                    folio=f"SAL-{placa}-{historial.fecha_salida:%Y%m%d}",
                    placa=placa,
                    fecha_entrada=entrada,
                    fecha_salida=datetime.combine(historial.fecha_salida, historial.hora_salida),
                    minutos_estadia=(datetime.combine(historial.fecha_salida, historial.hora_salida) - entrada).total_seconds() // 60,
                    total_pagado=float(historial.importe),
                    cajero="SISTEMA",
                    etiqueta="ORIGINAL"
                )
                
                imprimir_ticket_red(ticket_bytes)
            except Exception as e:
                print(f"Error imprimiendo ticket: {e}")

    elif parsed.normalized_status == "rechazado":
        payment_transaction.estado = "rechazado"
    elif parsed.normalized_status == "cancelado":
        payment_transaction.estado = "cancelado"
    else:
        payment_transaction.estado = "pendiente"

    db.commit()

    return {
        "status": "processed",
        "provider": provider.provider_name,
        "lookup_field": parsed.lookup_field,
        "lookup_value": parsed.lookup_value,
        "transaction_status": payment_transaction.estado,
    }


@router.get("/pagos/{preferencia_id}", response_model=PaymentTransactionResponse)
def obtener_estado_pago(
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
