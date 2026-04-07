from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.datetime_utils import now_local_naive
from core.payment_provider import ParsedWebhookEvent
from core.parking_pricing import calcular_importe_por_minutos, calcular_minutos_estadia
from core.parking_ticket_service import (
    construir_ticket_salida,
    guardar_ticket_bytes,
    imprimir_lote_tickets_salida,
)
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.payment_transaction import PaymentTransaction
from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario


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

    return encargado_nombre


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


def _construir_ticket_salida_historial(historial: HistoryEstacionamiento, cajero_nombre: str, etiqueta: str) -> bytes:
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
    )


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


def registrar_salida_tarjeta_pendiente(
    db: Session,
    current_user: Usuario,
    placa: str,
    provider_name: str,
    email: str | None = None,
) -> ParkingExitResult:
    context = _crear_contexto_salida(db, current_user, placa, metodo_pago="tarjeta")
    selected_provider = (provider_name or "stripe").strip().lower()

    tx_pendiente = db.query(PaymentTransaction).filter(
        PaymentTransaction.placa == context.placa,
        PaymentTransaction.estado == PaymentTransaction.ESTADO_PENDIENTE,
    ).order_by(desc(PaymentTransaction.created_at)).first()

    if tx_pendiente:
        metadata_existente = _metadata_from_transaction(tx_pendiente)
        checkout_existente = metadata_existente.get("checkout_url")
        provider_existente = metadata_existente.get("provider", selected_provider)

        historial_pendiente = db.query(HistoryEstacionamiento).filter(
            HistoryEstacionamiento.payment_transaction_id == tx_pendiente.id,
            HistoryEstacionamiento.pagado == False,
        ).first()

        if checkout_existente and historial_pendiente:
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

    from core.payment_provider import get_payment_provider

    try:
        preferencia_id, checkout_url = get_payment_provider(selected_provider).create_checkout(
            placa=context.placa,
            monto=context.importe,
            email=email,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al crear checkout: {str(exc)}") from exc

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

    folio = str(historial.id)
    ticket_bytes = construir_ticket_salida(
        folio=folio,
        placa=context.placa,
        fecha_entrada=datetime.combine(context.fecha_entrada, context.hora_entrada),
        fecha_salida=context.salida_dt,
        minutos_estadia=context.total_minutos,
        total_pagado=float(context.importe),
        cajero=context.cajero_nombre,
        metodo_pago="En linea",
        etiqueta="ORIGINAL",
    )
    ticket_path = guardar_ticket_bytes("salida", context.placa, context.salida_dt, ticket_bytes, suffix="_pendiente")

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
        ticket_bin=str(ticket_path),
        estado="pendiente",
        payment_transaction_id=payment_transaction.id,
        history_estacionamiento_id=historial.id,
    )


def procesar_webhook_pago(db: Session, provider, parsed: ParsedWebhookEvent) -> dict:
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
            PaymentTransaction.placa == parsed.lookup_value,
            PaymentTransaction.estado == PaymentTransaction.ESTADO_PENDIENTE,
        ).order_by(desc(PaymentTransaction.created_at)).first()

        if not payment_transaction:
            payment_transaction = db.query(PaymentTransaction).filter(
                PaymentTransaction.placa == parsed.lookup_value
            ).order_by(desc(PaymentTransaction.created_at)).first()
    else:
        raise HTTPException(status_code=400, detail="lookup_field no soportado")

    if not payment_transaction:
        print(f"No se encontro transaccion para {parsed.lookup_field}: {parsed.lookup_value}")
        return {"status": "not_found"}

    payment_transaction.webhook_timestamp = datetime.utcnow()
    existing_metadata = _metadata_from_transaction(payment_transaction)
    merged_metadata = {
        **existing_metadata,
        PaymentTransaction.METADATA_PROVIDER_EVENT_KEY: parsed.event_payload or {},
    }
    payment_transaction.metadata_mp = provider.serialize_event(merged_metadata)

    historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.placa == payment_transaction.placa,
        HistoryEstacionamiento.payment_transaction_id == payment_transaction.id,
    ).first()

    if parsed.normalized_status == "completado":
        if payment_transaction.estado == PaymentTransaction.ESTADO_COMPLETADO:
            if parsed.provider_transaction_id and not payment_transaction.payment_intent:
                payment_transaction.payment_intent = parsed.provider_transaction_id
            db.commit()
            return {
                "status": "processed_already",
                "provider": provider.provider_name,
                "lookup_field": parsed.lookup_field,
                "lookup_value": parsed.lookup_value,
                "transaction_status": payment_transaction.estado,
            }

        payment_transaction.estado = PaymentTransaction.ESTADO_COMPLETADO
        if parsed.provider_transaction_id:
            payment_transaction.payment_intent = parsed.provider_transaction_id

        if historial:
            historial.pagado = True
            _cerrar_vehiculo(db, historial.placa)

            try:
                cajero_nombre = _resolver_nombre_cajero(db, historial)
                ticket_bytes = _construir_ticket_salida_historial(historial, cajero_nombre, "ORIGINAL")
                ticket_copia_bytes = _construir_ticket_salida_historial(historial, cajero_nombre, "COPIA")

                impreso_ok, impresion_mensaje = imprimir_lote_tickets_salida([ticket_bytes, ticket_copia_bytes])
                if not impreso_ok:
                    print(f"Advertencia impresion salida tarjeta | {impresion_mensaje}")
            except Exception as exc:
                print(f"Error imprimiendo ticket: {exc}")

    elif parsed.normalized_status == "rechazado":
        if payment_transaction.estado != PaymentTransaction.ESTADO_COMPLETADO:
            payment_transaction.estado = PaymentTransaction.ESTADO_RECHAZADO
    elif parsed.normalized_status == "cancelado":
        if payment_transaction.estado != PaymentTransaction.ESTADO_COMPLETADO:
            payment_transaction.estado = PaymentTransaction.ESTADO_CANCELADO
    else:
        if payment_transaction.estado != PaymentTransaction.ESTADO_COMPLETADO:
            payment_transaction.estado = PaymentTransaction.ESTADO_PENDIENTE

    db.commit()

    return {
        "status": "processed",
        "provider": provider.provider_name,
        "lookup_field": parsed.lookup_field,
        "lookup_value": parsed.lookup_value,
        "transaction_status": payment_transaction.estado,
    }