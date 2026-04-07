import json
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class InvoiceRequest(Base):
    __tablename__ = "invoice_requests"

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_ISSUED = "issued"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    SOURCE_PAYMENT_TRANSACTION = "payment_transaction"
    SOURCE_HISTORY_EXIT = "history_exit"
    SOURCE_MANUAL = "manual"

    id: Mapped[int] = mapped_column(primary_key=True)
    fiscal_customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default=STATUS_PENDING, nullable=False, index=True)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="MXN", nullable=False)
    invoice_payload_json: Mapped[str | None] = mapped_column(String(8000), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(50), default="facturapi", nullable=False)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    access_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    provider_last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def payload_as_dict(self) -> dict:
        if not self.invoice_payload_json:
            return {}
        try:
            parsed = json.loads(self.invoice_payload_json)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @classmethod
    def build_payload(cls, payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=True)
