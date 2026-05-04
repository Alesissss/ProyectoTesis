import uuid
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Index, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.rol import Rol
    from app.models.baseline_emg import BaselineEmg
    from app.models.evaluacion import Evaluacion


class Usuario(Base, AuditMixin):
    __tablename__ = "usuarios"
    __table_args__ = (
        # idx_usuarios_email existe en DDL (redundante con UNIQUE pero declarado explícitamente)
        Index("idx_usuarios_email", "email"),
        Index("idx_usuarios_id_rol", "id_rol"),
    )

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    id_rol: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id_rol", ondelete="RESTRICT"), nullable=False
    )

    # Relaciones
    rol: Mapped["Rol"] = relationship("Rol", back_populates="usuarios")
    baselines: Mapped[List["BaselineEmg"]] = relationship("BaselineEmg", back_populates="usuario")
    evaluaciones: Mapped[List["Evaluacion"]] = relationship("Evaluacion", back_populates="usuario")
