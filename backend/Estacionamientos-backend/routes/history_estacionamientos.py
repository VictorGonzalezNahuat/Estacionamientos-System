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
    historial = db.query(HistoryEstacionamiento).filter(HistoryEstacionamiento.fecha_salida == hoy).all()
    return historial

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

        if current_turno.estado != "cerrado":
            raise HTTPException(status_code=409, detail="El turno no se ha cerrado aun")
        
    if encargado:
        usuario = db.query(Usuario).filter(Usuario.nombre == encargado).first()

        if not usuario:
            raise HTTPException(status_code=404, detail="Encargado no encontrado")

        query = query.filter(HistoryEstacionamiento.encargado_id == usuario.id)

    historial = query.all()

    return historial

@router.get("/rango")
def historial_rango(
    desde: date,
    hasta: date,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if desde > hasta:
        raise HTTPException(status_code=400, detail="Rango de fechas inválido")

    historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.fecha_salida >= desde,
        HistoryEstacionamiento.fecha_salida <= hasta
    ).all()

    return historial
