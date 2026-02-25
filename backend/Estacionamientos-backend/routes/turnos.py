from datetime import date, datetime, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user, verify_password
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.turno import Turno
from models.usuario import Usuario
from schemas.auth import ConfirmPasswordRequest
from schemas.turno import TurnoCreate, TurnoResponse


router = APIRouter()


@router.get("/mi-turno")
def mi_turno(current_user: Usuario = Depends(get_current_user), db:Session = Depends(get_db)):
    turno = db.query(Turno).filter(Turno.encargado_id == current_user.id, Turno.estado == "activo").first()

    if not turno:
        return {"abierto": False}
    
    return {"abierto": True,
            "turno_id": turno.id,
            "hora_apertura": turno.hora_inicio}


@router.post("/", response_model=TurnoResponse)
def crear_turno(
    data: ConfirmPasswordRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    
    existe_turno = (
        db.query(Turno)
        .filter(
            Turno.encargado_id == current_user.id,
            Turno.estado == "activo"
        )
        .first()
    )

    if existe_turno:
        raise HTTPException(
            status_code=400,
            detail="Ya hay turno activo de este encargado"
        )

    nuevo_turno = Turno(
        encargado_id=current_user.id,
        fecha=date.today(),
        hora_inicio=datetime.now().time(),
        estado="activo",
        hora_fin=None,
        fecha_fin=None
    )

    db.add(nuevo_turno)
    db.commit()
    db.refresh(nuevo_turno)

    return nuevo_turno

@router.delete("/", response_model=TurnoResponse)
def cerrar_turno(data: ConfirmPasswordRequest, current_user: Usuario = Depends(get_current_user), db:Session = Depends(get_db)):
    
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Contraseña Incorrecta")
    
    existe_turno = db.query(Turno).filter(Turno.encargado_id == Usuario.id, Turno.estado == "activo").first()

    if not existe_turno:
        raise HTTPException(status_code=404, detail="No existe turno abierto para este encargado")

    existe_turno.hora_fin = datetime.now().time()
    existe_turno.fecha_fin = date.today()
    existe_turno.estado = "cerrado"
    

    db.commit()
    db.refresh(existe_turno)

    return existe_turno


