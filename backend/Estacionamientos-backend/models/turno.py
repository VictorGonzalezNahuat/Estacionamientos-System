from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Turno(Base):
    __tablename__ = "turnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    encargado_id: Mapped[int] = mapped_column(nullable=False)
    fecha: Mapped[date] = mapped_column(Date())
    hora_inicio: Mapped[time] = mapped_column(Time())
    estado: Mapped[str] = mapped_column(String(100))
    hora_fin: Mapped[time] = mapped_column(Time())
    fecha_fin: Mapped[date] = mapped_column(Date())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)


