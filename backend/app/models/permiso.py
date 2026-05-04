from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.rol_permiso import RolPermiso


class Permiso(Base, AuditMixin):
    __tablename__ = "permisos"

    id_permiso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo_permiso: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relaciones
    rol_permisos: Mapped[List["RolPermiso"]] = relationship("RolPermiso", back_populates="permiso")
