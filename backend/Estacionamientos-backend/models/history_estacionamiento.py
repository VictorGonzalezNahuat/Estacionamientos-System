from datetime import date, time, datetime
from sqlalchemy import Date, Float, Integer, Time, DateTime, String
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
    
    
    

