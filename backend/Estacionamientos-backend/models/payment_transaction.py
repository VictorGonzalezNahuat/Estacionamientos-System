from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    preferencia_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    placa: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default="pendiente", index=True)  # pendiente, completado, cancelado, rechazado
    metadata_mp: Mapped[str | None] = mapped_column(String(5000), nullable=True)  # JSON con respuesta del proveedor de pagos
    webhook_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
