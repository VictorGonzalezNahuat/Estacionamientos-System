import json
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_COMPLETADO = "completado"
    ESTADO_CANCELADO = "cancelado"
    ESTADO_RECHAZADO = "rechazado"

    METADATA_PROVIDER_KEY = "provider"
    METADATA_CHECKOUT_URL_KEY = "checkout_url"
    METADATA_CREATED_AT_KEY = "created_at"
    METADATA_EXIT_CONTEXT_KEY = "exit_context"
    METADATA_PROVIDER_EVENT_KEY = "provider_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    preferencia_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    payment_intent: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    placa: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default=ESTADO_PENDIENTE, index=True)
    metadata_mp: Mapped[str | None] = mapped_column(String(5000), nullable=True)  # JSON con respuesta del proveedor de pagos
    webhook_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def metadata_as_dict(self) -> dict:
        if not self.metadata_mp:
            return {}
        try:
            parsed = json.loads(self.metadata_mp)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @classmethod
    def build_metadata(cls, payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=True)
