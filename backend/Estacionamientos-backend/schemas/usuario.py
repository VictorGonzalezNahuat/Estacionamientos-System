from typing import Optional

from pydantic import BaseModel, field_validator


class UserRoles(BaseModel):
    admin: bool = False
    encargado: bool = False


class UsuarioBase(BaseModel):
    codigo: int
    nombre: Optional[str] = None
    comision: Optional[float] = 0.0
    rol: UserRoles | None = None
    observaciones: Optional[str] = None
    email: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    comision: Optional[float] = None
    rol: UserRoles | None = None
    observaciones: Optional[str] = None


class UsuarioResponse(UsuarioBase):
    id: int

    @field_validator("rol", mode="before")
    @classmethod
    def parse_rol(cls, value):
        if value is None or isinstance(value, UserRoles):
            return value
        if isinstance(value, str):
            return UserRoles.model_validate_json(value)
        if isinstance(value, dict):
            return UserRoles.model_validate(value)
        raise ValueError("Formato de rol inválido")

    class Config:
        from_attributes = True
