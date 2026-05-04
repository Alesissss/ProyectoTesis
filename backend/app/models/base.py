"""
Mixin de auditoría compartido por todas las entidades de negocio.
Los tres campos corresponden al estándar del proyecto:
  estado_registro  → soft-delete
  usuario_registro → quién creó el registro (NULL si fue desde la BD directamente)
  fecha_registro   → timestamp de creación
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    estado_registro: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    usuario_registro: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
