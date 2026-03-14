from sqlalchemy import DECIMAL, JSON, Column, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Tarifa(Base):
    __tablename__ = "tarifas"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_vehiculo: Mapped[str | None] = mapped_column(String(100))
    hora: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.00)
    fraccion: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.00)
    medio_dia: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.00)
    diario: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.00)
    observaciones: Mapped[str | None] = mapped_column(String(255))
    eliminado: Mapped[int] = mapped_column(Integer, default=0)
    default: Mapped[int] = mapped_column(Integer, default=0) 