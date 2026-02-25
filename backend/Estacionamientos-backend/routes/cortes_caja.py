from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.security import get_current_user
from database import get_db

from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario


router = APIRouter()


@router.get("/corte")
def cortar_caja(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    #TODO cambiar la logica en como cierra turnos -> pendiente_corte, implementar este METODO
    turno = db.query(Turno).filter(Turno.encargado_id == Usuario.id, Turno.estado == "cerrado")
    if not turno:
        raise HTTPException(status_code=404, detail="No se encontró turno para el corte")


    return {
        "estado": "cortado_prueba"
    }
