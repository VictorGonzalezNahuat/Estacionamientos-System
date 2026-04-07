from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator


class InvoiceEmitRequest(BaseModel):
    fiscal_customer_id: int = Field(gt=0)
    history_estacionamiento_id: int = Field(gt=0)
    placa: str = Field(min_length=1, max_length=100)
    fecha_salida: date
    hora_salida: time
    importe: float = Field(gt=0)
    send_email: bool = True
    notes: str | None = Field(default=None, max_length=500)
    recaptcha_token: str = Field(min_length=20, max_length=4096)

    @field_validator("placa")
    @classmethod
    def normalize_placa(cls, value: str) -> str:
        placa = value.strip().upper()
        if not placa:
            raise ValueError("placa no puede estar vacia")
        return placa

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("recaptcha_token")
    @classmethod
    def normalize_recaptcha_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("recaptcha_token requerido")
        return token


class InvoiceEmitResponse(BaseModel):
    invoice_request_id: int
    status: str
    fiscal_customer_id: int
    source_type: str
    source_id: str
    idempotency_key: str
    access_token: str
    access_token_expires_at: datetime
    created_at: datetime
    message: str


class InvoiceRequestStatusResponse(BaseModel):
    invoice_request_id: int
    status: str
    fiscal_customer_id: int
    issued_at: datetime | None = None
    total: float | None = None
    currency: str | None = None
    documents_ready: bool
    can_cancel: bool
    attempts: int
    created_at: datetime
    updated_at: datetime


class InvoiceCancelRequest(BaseModel):
    motivo: str = Field(min_length=1, max_length=10)
    comentario: str | None = Field(default=None, max_length=500)

    @field_validator("motivo")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("comentario")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class InvoiceCancelResponse(BaseModel):
    invoice_request_id: int
    status: str
    cancelled_at: datetime | None = None
    message: str
