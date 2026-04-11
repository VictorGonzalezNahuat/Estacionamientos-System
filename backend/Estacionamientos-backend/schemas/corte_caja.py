from datetime import date, time

from pydantic import BaseModel


class CorteCajaBase(BaseModel):
    id_turno: int
    fecha_inicio: date
    hora_inicio: time
    fecha_fin: date
    hora_fin: time
    total_calculado: float
    total_declarado: float
    diferencia: float
    total_efectivo: float
    total_tarjeta: float


class CorteCajaCreate(BaseModel):
    turno_id: int
    total_declarado: float


class CorteCajaResponse(CorteCajaBase):
    id: int

    class Config:
        from_attributes = True


class CorteCajaResumenResponse(BaseModel):
    turno_id: int
    total_efectivo: float
    total_tarjeta: float
    total_total: float

    class Config:
        from_attributes = True
