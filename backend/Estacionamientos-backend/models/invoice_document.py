from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class InvoiceDocument(Base):
    __tablename__ = "invoice_documents"

    STATUS_ISSUED = "issued"
    STATUS_CANCELLED = "cancelled"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_request_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    uuid_fiscal: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    serie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    folio: Mapped[str | None] = mapped_column(String(30), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subtotal: Mapped[float | None] = mapped_column(Float, nullable=True)
    taxes: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="MXN", nullable=False)
    xml_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verification_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=STATUS_ISSUED, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
