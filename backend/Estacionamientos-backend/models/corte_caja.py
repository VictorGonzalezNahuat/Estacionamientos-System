from datetime import date, time

from sqlalchemy import DECIMAL, Date, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CorteCaja(Base):
    __tablename__ = "cortes_caja"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_turno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fecha_inicio: Mapped[date] = mapped_column(Date(), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time(), nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date(), nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time(), nullable=False)
    total_calculado: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    total_declarado: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    diferencia: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    total_efectivo: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    total_tarjeta: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
