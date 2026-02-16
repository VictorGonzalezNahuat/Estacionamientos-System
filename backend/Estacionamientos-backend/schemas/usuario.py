from typing import Any, Dict, Optional

from pydantic import BaseModel


class UsuarioBase(BaseModel):
    codigo: int
    nombre: Optional[str] = None
    comision: Optional[float] = 0.0
    rol: str | None
    observaciones: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioResponse(UsuarioBase):
    id: int

    class Config:
        from_attributes = True
