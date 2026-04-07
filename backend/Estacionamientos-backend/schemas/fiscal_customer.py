from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator


class FiscalCustomerUpsertRequest(BaseModel):
    rfc: str = Field(min_length=12, max_length=13)
    razon_social: str = Field(min_length=1, max_length=255)
    codigo_postal: str = Field(min_length=5, max_length=5)
    regimen_fiscal: str = Field(min_length=1, max_length=50)
    uso_cfdi_receptor: str = Field(default="G03", min_length=3, max_length=3)
    nombre_contacto: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=20)
    history_estacionamiento_id: int = Field(gt=0)
    placa: str = Field(min_length=1, max_length=100)
    fecha_salida: date
    hora_salida: time
    importe: float = Field(gt=0)
    recaptcha_token: str = Field(min_length=20, max_length=4096)

    @field_validator("rfc")
    @classmethod
    def normalize_rfc(cls, value: str) -> str:
        rfc = value.strip().upper()
        if len(rfc) not in {12, 13}:
            raise ValueError("RFC invalido. Debe tener 12 o 13 caracteres")
        return rfc

    @field_validator("razon_social", "regimen_fiscal")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Este campo no puede estar vacio")
        return normalized

    @field_validator("codigo_postal")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        cp = value.strip()
        if len(cp) != 5 or not cp.isdigit():
            raise ValueError("Codigo postal debe ser de 5 digitos")
        return cp

    @field_validator("uso_cfdi_receptor")
    @classmethod
    def normalize_uso_cfdi(cls, value: str) -> str:
        uso = value.strip().upper()
        if len(uso) != 3:
            raise ValueError("uso_cfdi_receptor debe tener 3 caracteres")
        return uso

    @field_validator("nombre_contacto", "email", "telefono")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("placa")
    @classmethod
    def normalize_placa(cls, value: str) -> str:
        placa = value.strip().upper()
        if not placa:
            raise ValueError("placa no puede estar vacia")
        return placa

    @field_validator("recaptcha_token")
    @classmethod
    def normalize_recaptcha_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("recaptcha_token requerido")
        return token


class FiscalCustomerResponse(BaseModel):
    id: int
    rfc: str
    razon_social: str
    codigo_postal: str
    regimen_fiscal: str
    uso_cfdi_receptor: str
    nombre_contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
