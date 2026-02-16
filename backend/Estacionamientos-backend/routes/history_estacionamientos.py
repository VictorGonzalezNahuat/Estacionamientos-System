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
    historial = db.query(HistoryEstacionamiento).filter(HistoryEstacionamiento.fecha_salida == hoy)

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
