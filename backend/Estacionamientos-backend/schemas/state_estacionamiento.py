from typing import Optional
from pydantic import BaseModel

class StateEstacionamientoBase(BaseModel):
    id: int
    total_espacios: int
    espacios_ocupados: int
    espacios_disponibles: Optional[int]

