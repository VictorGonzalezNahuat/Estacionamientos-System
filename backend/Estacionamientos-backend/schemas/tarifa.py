from typing import Any, Dict, Optional

from pydantic import BaseModel


class TarifaBase(BaseModel):
    numero: int
    tipo_vehiculo: Optional[str] = ""
    hora: Optional[float] = 0.0
    fraccion: Optional[float] = 0.0
    medio_dia: Optional[float] = 0.0
    diario: Optional[float] = 0.0
    observaciones: Optional[str] = ""
    eliminado: int = 0
    default: int = 0


class TarifaRespose(TarifaBase):
    id: int
