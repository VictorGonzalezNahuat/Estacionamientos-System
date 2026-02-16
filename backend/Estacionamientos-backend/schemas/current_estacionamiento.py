from datetime import date, time
from typing import Optional
from pydantic import BaseModel, Field

class CurrentEstacionamientoCreate(BaseModel):
    placa: str

class CurrentEstacionamientoResponse(BaseModel):
    id: int
    placa: str
    tarifa_id: int
    encargado_id: int
    turno_id: int
    fecha_entrada: date
    hora_entrada: time

    class Config:
        orm_mode = True

