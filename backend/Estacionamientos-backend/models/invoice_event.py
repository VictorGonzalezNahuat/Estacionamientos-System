import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class InvoiceEvent(Base):
    __tablename__ = "invoice_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_request_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload_summary_json: Mapped[str | None] = mapped_column(String(8000), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @classmethod
    def build_payload(cls, payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=True)
