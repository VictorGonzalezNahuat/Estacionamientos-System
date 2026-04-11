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
    payment_intent: Optional[str] = None
    placa: str
    monto: float
    estado: str
    webhook_timestamp: Optional[datetime] = None
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
    provider: str
    placa: str
    monto: float
    fecha_salida: str
    hora_salida: str
    minutos_estadia: int
    ticket_bin: str
    estado: str = "pendiente"
    history_estacionamiento_id: Optional[int] = None

    class Config:
        from_attributes = True


class PagoEstadoDetalleResponse(BaseModel):
    preferencia_id: str
    payment_intent: Optional[str] = None
    placa: str
    estado_transaccion: str
    transaccion_exitosa: bool
    mensaje_estado: str
    pagado: bool
    metodo_pago: Optional[str] = None
    importe: Optional[float] = None
    webhook_timestamp: Optional[datetime] = None


class CancelarPagoRequest(BaseModel):
    provider: Optional[Literal["stripe", "mercadopago"]] = None
    motivo: str


class CancelarPagoResponse(BaseModel):
    preferencia_id: str
    estado_transaccion: str
    cancelado_local: bool
    cancelado_remoto: bool
    provider: str
    motivo: Optional[str] = None
    detalle: Optional[str] = None
