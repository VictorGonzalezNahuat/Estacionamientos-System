from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class FiscalCustomer(Base):
    __tablename__ = "fiscal_customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False, unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_postal: Mapped[str] = mapped_column(String(5), nullable=False)
    regimen_fiscal: Mapped[str] = mapped_column(String(50), nullable=False)
    uso_cfdi_receptor: Mapped[str] = mapped_column(String(3), default="G03", nullable=False)
    nombre_contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_invoiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
