from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from core.parking_exit_service import cancelar_ticket_por_historial, reimprimir_ticket_salida_desde_historial
from core.security import get_current_user
from database import get_db
from models.history_estacionamiento import HistoryEstacionamiento
from models.ticket_cancelado import TicketCancelado
from models.turno import Turno
from models.usuario import Usuario
from schemas.history_estacionamiento import CancelarTicketHistorialRequest


router = APIRouter()
REIMPRESION_LEYENDA = "Este ticket ha sido reimpreso desde el sistema"


@router.get("/hoy")
def historial_hoy(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):

    hoy = date.today()
    historiales = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.fecha_salida == hoy,
        HistoryEstacionamiento.corte_id == None,
        HistoryEstacionamiento.cancelado == 0,
    ).all()
    
    # Verificar si hay turnos sin cerrar o cortes pendientes
    hay_turnos_sin_cerrar = False
    hay_cortes_pendientes = False
    for historial in historiales:
        historial_turno = db.query(Turno).filter(Turno.id == historial.turno_id).first()
        if historial_turno:
            if historial_turno.estado == "activo":
                hay_turnos_sin_cerrar = True
            elif historial_turno.estado == "pendiente_corte":
                hay_cortes_pendientes = True

    advertencia = None
    if hay_turnos_sin_cerrar:
        advertencia = "Hay vehículos con turno sin cerrar"
    elif hay_cortes_pendientes:
        advertencia = "Hay cortes de caja pendientes"

    return {
        "data": historiales,
        "advertencia": advertencia
    }

@router.get("/dia/filtrar")
def historial_dia_con_filtro(
    fecha: date,
    turno: Optional[int] = None,
    encargado: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    query = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.fecha_salida == fecha,
        HistoryEstacionamiento.corte_id == None,
        HistoryEstacionamiento.cancelado == 0,
    )
    if turno is not None:
        query = query.filter(HistoryEstacionamiento.turno_id == turno)
        current_turno = db.query(Turno).filter(Turno.id == turno).first()
        
        if not current_turno:
            raise HTTPException(status_code=404, detail="No se ha encontrado el turno")
        
    if encargado:
        usuario = db.query(Usuario).filter(Usuario.nombre == encargado).first()

        if not usuario:
            raise HTTPException(status_code=404, detail="Encargado no encontrado")

        query = query.filter(HistoryEstacionamiento.encargado_id == usuario.id)

    historial = query.all()

    # Obtener IDs únicos de turno del historial y verificar si hay sin cerrar
    turno_ids = {h.turno_id for h in historial}
    hay_turnos_sin_cerrar = False

    for turno_id in turno_ids:
        turno_obj = db.query(Turno).filter(Turno.id == turno_id).first()

        if not turno_obj:
            raise HTTPException(status_code=404, detail="Turno no encontrado")

        if turno_obj.estado == "activo":
            hay_turnos_sin_cerrar = True

    return {
        "data": historial,
        "advertencia": "Hay vehículos con turno sin cerrar" if hay_turnos_sin_cerrar else None
    }

@router.get("/rango")
def historial_rango(
    desde: date,
    hasta: date,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if desde > hasta:
        raise HTTPException(status_code=400, detail="Rango de fechas inválido")

    historiales = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.fecha_salida >= desde,
        HistoryEstacionamiento.fecha_salida <= hasta,
        HistoryEstacionamiento.corte_id == None,
        HistoryEstacionamiento.cancelado == 0,
    ).all()

    # Verificar si hay turnos sin cerrar o cortes pendientes
    hay_turnos_sin_cerrar = False
    hay_cortes_pendientes = False
    for historial in historiales:
        historial_turno = db.query(Turno).filter(Turno.id == historial.turno_id).first()
        if historial_turno:
            if historial_turno.estado == "activo":
                hay_turnos_sin_cerrar = True
            elif historial_turno.estado == "pendiente_corte":
                hay_cortes_pendientes = True

    advertencia = None
    if hay_turnos_sin_cerrar:
        advertencia = "Hay vehículos con turno sin cerrar"
    elif hay_cortes_pendientes:
        advertencia = "Hay cortes de caja pendientes"

    return {
        "data": historiales,
        "advertencia": advertencia
    }


@router.get("/reimpresion/ultimos")
def historial_ultimos_para_reimpresion(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    _ = current_user
    historiales = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.cancelado == 0,
    ).order_by(desc(HistoryEstacionamiento.id)).limit(50).all()

    return {
        "data": [
            {
                "id": historial.id,
                "tarifa_id": historial.tarifa_id,
                "encargado_id": historial.encargado_id,
                "turno_id": historial.turno_id,
                "fecha_entrada": historial.fecha_entrada,
                "hora_entrada": historial.hora_entrada,
                "fecha_salida": historial.fecha_salida,
                "hora_salida": historial.hora_salida,
                "placa": historial.placa,
                "importe": historial.importe,
                "metodo_pago": historial.metodo_pago,
                "pagado": historial.pagado,
                "updated_at": historial.updated_at,
            }
            for historial in historiales
        ]
    }


@router.post("/reimpresion/{historial_id}")
def reimprimir_ticket_salida(
    historial_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    historial = db.query(HistoryEstacionamiento).filter(HistoryEstacionamiento.id == historial_id).first()

    if not historial:
        raise HTTPException(status_code=404, detail="Registro de salida no encontrado")

    if int(getattr(historial, "cancelado", 0)) == 1:
        raise HTTPException(status_code=409, detail="No se puede reimprimir un ticket cancelado")

    impreso_ok, impresion_mensaje, ticket_copias = reimprimir_ticket_salida_desde_historial(
        db,
        historial,
        leyenda_reimpresion=REIMPRESION_LEYENDA,
    )

    return {
        "mensaje": "Ticket de salida reimpreso",
        "ticket_impreso": impreso_ok,
        "impresion_mensaje": impresion_mensaje,
        "ticket_copias": ticket_copias,
    }


@router.post("/cancelar/{historial_id}")
def cancelar_ticket_historial(
    historial_id: int,
    payload: CancelarTicketHistorialRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cancelar_ticket_por_historial(
        db=db,
        historial_id=historial_id,
        current_user_id=current_user.id,
        motivo=payload.motivo,
    )


@router.get("/cancelados")
def listar_tickets_cancelados(
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    placa: Optional[str] = None,
    cancelado_por: Optional[int] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user

    if desde and hasta and desde > hasta:
        raise HTTPException(status_code=400, detail="Rango de fechas inválido")

    query = db.query(TicketCancelado, HistoryEstacionamiento).join(
        HistoryEstacionamiento,
        HistoryEstacionamiento.id == TicketCancelado.history_estacionamiento_id,
    )

    if desde:
        query = query.filter(HistoryEstacionamiento.fecha_salida >= desde)
    if hasta:
        query = query.filter(HistoryEstacionamiento.fecha_salida <= hasta)
    if placa:
        query = query.filter(HistoryEstacionamiento.placa == placa.strip().upper())
    if cancelado_por is not None:
        query = query.filter(TicketCancelado.cancelado_por == cancelado_por)

    resultados = query.order_by(desc(TicketCancelado.fecha_cancelacion)).all()

    return {
        "data": [
            {
                "ticket_cancelado_id": ticket_cancelado.id,
                "history_estacionamiento_id": historial.id,
                "payment_transaction_id": ticket_cancelado.payment_transaction_id,
                "placa": historial.placa,
                "turno_id": historial.turno_id,
                "encargado_id": historial.encargado_id,
                "fecha_entrada": historial.fecha_entrada,
                "hora_entrada": historial.hora_entrada,
                "fecha_salida": historial.fecha_salida,
                "hora_salida": historial.hora_salida,
                "importe": float(historial.importe),
                "metodo_pago": historial.metodo_pago,
                "pagado": bool(historial.pagado),
                "cancelado": int(historial.cancelado),
                "motivo": ticket_cancelado.motivo,
                "cancelado_por": ticket_cancelado.cancelado_por,
                "fecha_cancelacion": ticket_cancelado.fecha_cancelacion,
            }
            for ticket_cancelado, historial in resultados
        ]
    }
