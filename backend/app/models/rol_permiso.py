from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.rol import Rol
    from app.models.permiso import Permiso


class RolPermiso(Base, AuditMixin):
    __tablename__ = "rol_permiso"

    id_rol: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id_rol", ondelete="RESTRICT"), primary_key=True
    )
    id_permiso: Mapped[int] = mapped_column(
        Integer, ForeignKey("permisos.id_permiso", ondelete="RESTRICT"), primary_key=True
    )

    # Relaciones
    rol: Mapped["Rol"] = relationship("Rol", back_populates="rol_permisos")
    permiso: Mapped["Permiso"] = relationship("Permiso", back_populates="rol_permisos")
