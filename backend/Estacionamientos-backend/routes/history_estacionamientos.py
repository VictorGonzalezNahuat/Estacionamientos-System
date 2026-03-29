from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.security import get_current_user
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario
from schemas.current_estacionamiento import CurrentEstacionamientoCreate


router = APIRouter()


@router.get("/hoy")
def historial_hoy(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):

    hoy = date.today()
    historiales = db.query(HistoryEstacionamiento).filter(HistoryEstacionamiento.fecha_salida == hoy).all()
    
    # Verificar si hay turnos sin cerrar para la advertencia
    hay_turnos_sin_cerrar = False
    for historial in historiales:
        historial_turno = db.query(Turno).filter(Turno.id == historial.turno_id).first()
        if historial_turno and historial_turno.estado != "cerrado":
            hay_turnos_sin_cerrar = True
            break

    return {
        "data": historiales,
        "advertencia": "Hay vehículos con turno sin cerrar" if hay_turnos_sin_cerrar else None
    }

from typing import Optional
from fastapi import HTTPException

@router.get("/dia/filtrar")
def historial_dia_con_filtro(
    fecha: date,
    turno: Optional[int] = None,
    encargado: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    query = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.fecha_salida == fecha
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

        if turno_obj.estado != "cerrado":
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
        HistoryEstacionamiento.fecha_salida <= hasta
    ).all()

    # Verificar si hay turnos sin cerrar para la advertencia
    hay_turnos_sin_cerrar = False
    for historial in historiales:
        historial_turno = db.query(Turno).filter(Turno.id == historial.turno_id).first()
        if historial_turno and historial_turno.estado != "cerrado":
            hay_turnos_sin_cerrar = True
            break

    return {
        "data": historiales,
        "advertencia": "Hay vehículos con turno sin cerrar" if hay_turnos_sin_cerrar else None
    }
