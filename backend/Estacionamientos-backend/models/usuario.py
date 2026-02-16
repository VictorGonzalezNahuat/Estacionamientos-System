from sqlalchemy import DECIMAL, JSON, Column, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[int] = mapped_column(unique=True, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    comision: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00)
    rol: Mapped[str | None] = mapped_column(Text)
    observaciones: Mapped[str | None] = mapped_column(String(100))
