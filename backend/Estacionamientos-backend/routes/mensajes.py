from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user
from database import get_cloud_db, get_db
from models.mensaje import Mensaje
from models.turno import Turno
from models.usuario import Usuario
from schemas.mensaje import (
    MarcarMensajesLeidosRequest,
    MarcarMensajesLeidosResponse,
    MensajesPendientesResponse,
)

router = APIRouter()


@router.get("/pendientes", response_model=MensajesPendientesResponse)
def leer_mensaje_pendiente(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    db_cloud: Session = Depends(get_cloud_db),
):
    turno_activo = (
        db.query(Turno)
        .filter(
            Turno.encargado_id == current_user.id,
            Turno.estado == "activo",
        )
        .first()
    )

    if not turno_activo:
        raise HTTPException(status_code=404, detail="No hay turno activo")

    mensajes = (
        db_cloud.query(Mensaje)
        .filter(
            Mensaje.turno_id == turno_activo.id,
            Mensaje.estado == "pendiente",
        )
        .order_by(Mensaje.fecha_enviado.asc())
        .all()
    )

    return {
        "total_pendientes": len(mensajes),
        "mensajes": mensajes,
    }


@router.patch("/marcar-leidos", response_model=MarcarMensajesLeidosResponse)
def marcar_mensajes_como_leidos(
    data: MarcarMensajesLeidosRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    db_cloud: Session = Depends(get_cloud_db),
):
    turno_activo = (
        db.query(Turno)
        .filter(
            Turno.encargado_id == current_user.id,
            Turno.estado == "activo",
        )
        .first()
    )

    if not turno_activo:
        raise HTTPException(status_code=404, detail="No hay turno activo")

    if not data.ids:
        return {"total_marcados": 0, "ids_marcados": []}

    mensajes = (
        db_cloud.query(Mensaje)
        .filter(
            Mensaje.turno_id == turno_activo.id,
            Mensaje.id.in_(data.ids),
            Mensaje.estado == "pendiente",
        )
        .all()
    )

    for mensaje in mensajes:
        mensaje.estado = "leido"

    db_cloud.commit()

    return {
        "total_marcados": len(mensajes),
        "ids_marcados": [mensaje.id for mensaje in mensajes],
    }
