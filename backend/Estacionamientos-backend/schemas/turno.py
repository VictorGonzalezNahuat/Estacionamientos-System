from datetime import date, time
from typing import Optional
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
    fecha_fin: date

    class Config:
        orm_mode = True

