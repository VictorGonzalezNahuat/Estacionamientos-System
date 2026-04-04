from datetime import date, time
from typing import Literal, Optional
from pydantic import BaseModel, Field

class TurnoCreate(BaseModel):
    encargado_id: int

class TurnoResponse(BaseModel):
    id: int
    encargado_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time | None
    estado: str
    fecha_fin: Optional[date]

    class Config:
        orm_mode = True


class MiTurnoResponse(BaseModel):
    estado: Literal["sin-turno", "abierto", "pendiente-corte"]
    turno_id: Optional[int] = None
    hora_apertura: Optional[time] = None

