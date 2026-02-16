from datetime import date, time, datetime
from sqlalchemy import Date, Time, DateTime, String, Integer
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
    

