from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class StateEstacionamiento(Base):
    __tablename__ = "state_estacionamiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    total_espacios: Mapped[int] = mapped_column(Integer)
    espacios_ocupados: Mapped[int] = mapped_column(Integer)
    espacios_disponibles: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

