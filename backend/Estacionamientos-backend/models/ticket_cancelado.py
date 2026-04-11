from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TicketCancelado(Base):
    __tablename__ = "tickets_cancelados"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_estacionamiento_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    payment_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)
    cancelado_por: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fecha_cancelacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
