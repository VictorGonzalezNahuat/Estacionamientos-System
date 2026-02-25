from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.security import get_current_user
from database import get_db

from models.state_estacionamiento import StateEstacionamiento
from models.usuario import Usuario


router = APIRouter()


@router.get("/estado")
def historial_hoy(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(StateEstacionamiento).first()
