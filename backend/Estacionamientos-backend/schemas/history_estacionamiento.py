from datetime import date, time
from typing import Optional
from pydantic import BaseModel, Field

class HistoryEstacionamientoBase(BaseModel):
    id: int
    tarifa_id: int
    encargado_id: int
    turno_id: int
    fecha_entrada: date
    hora_entrada: time
    fecha_salida: date
    hora_salida: time
    placa: str
    importe: float

