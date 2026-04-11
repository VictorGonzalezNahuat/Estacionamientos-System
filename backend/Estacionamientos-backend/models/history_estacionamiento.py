from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Float, Integer, String, Time, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class HistoryEstacionamiento(Base):
    __tablename__ = "history_estacionamiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    tarifa_id: Mapped[int] = mapped_column(Integer)
    encargado_id: Mapped[int] = mapped_column(nullable=False)
    turno_id: Mapped[int] = mapped_column(Integer)
    fecha_entrada: Mapped[date] = mapped_column(Date())
    hora_entrada: Mapped[time] = mapped_column(Time())
    fecha_salida: Mapped[date] = mapped_column(Date())
    hora_salida: Mapped[time] = mapped_column(Time())
    placa: Mapped[str] = mapped_column(String(100))
    importe: Mapped[float] = mapped_column(Float)
    metodo_pago: Mapped[str] = mapped_column(String(50), default="efectivo")  # 'efectivo' | 'tarjeta'
    pagado: Mapped[bool] = mapped_column(Boolean, default=False)  # True cuando pago confirmado
    cancelado: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)  # 0 activo | 1 cancelado
    payment_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # FK a payment_transactions
    corte_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)




