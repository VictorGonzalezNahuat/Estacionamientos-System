from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from typing import Literal


class PaymentTransactionBase(BaseModel):
    preferencia_id: str
    placa: str
    monto: float
    estado: str = "pendiente"


class PaymentTransactionCreate(BaseModel):
    placa: str
    monto: float
    email: Optional[str] = None  # Email del cliente para proveedor de pago


class PaymentTransactionResponse(BaseModel):
    id: int
    preferencia_id: str
    placa: str
    monto: float
    estado: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalirTarjetaRequest(BaseModel):
    placa: str
    email: Optional[str] = None  # Email para enviar recibo
    provider: Optional[Literal["stripe", "mercadopago"]] = None


class SalirTarjetaResponse(BaseModel):
    mensaje: str
    preferencia_id: str
    checkout_url: str
    placa: str
    monto: float
    fecha_salida: str
    hora_salida: str
    minutos_estadia: int
    ticket_bin: str

    class Config:
        from_attributes = True
