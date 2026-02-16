from datetime import date, time, datetime
from sqlalchemy import Date, Integer, Time, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CurrentEstacionamiento(Base):
    __tablename__ = "current_estacionamiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    encargado_id: Mapped[int] = mapped_column(nullable=False)
    placa: Mapped[str] = mapped_column(String(100))
    tarifa_id: Mapped[int] = mapped_column(Integer)
    turno_id: Mapped[int] = mapped_column(Integer)
    fecha_entrada: Mapped[date] = mapped_column(Date())
    hora_entrada: Mapped[time] = mapped_column(Time())

