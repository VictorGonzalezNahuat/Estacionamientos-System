from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MensajeCreate(BaseModel):
    turno_id: int
    contenido: str
    estado: Optional[str] = "pendiente"


class MensajeUpdate(BaseModel):
    contenido: Optional[str] = None
    estado: Optional[str] = None


class MensajeResponse(BaseModel):
    id: int
    turno_id: int
    contenido: str
    admin_id: int
    estado: str
    fecha_enviado: datetime

    class Config:
        orm_mode = True


class MensajesPendientesResponse(BaseModel):
    total_pendientes: int
    mensajes: list[MensajeResponse]


class MarcarMensajesLeidosRequest(BaseModel):
    ids: list[int]


class MarcarMensajesLeidosResponse(BaseModel):
    total_marcados: int
    ids_marcados: list[int]
