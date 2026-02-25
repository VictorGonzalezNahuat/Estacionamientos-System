from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class StateEstacionamiento(Base):
    __tablename__ = "state_estacionamiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    total_espacios: Mapped[int] = mapped_column(Integer)
    espacios_ocupados: Mapped[int] = mapped_column(Integer)
    espacios_disponibles: Mapped[int] = mapped_column(Integer)

