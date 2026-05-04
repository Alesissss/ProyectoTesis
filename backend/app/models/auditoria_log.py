import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.data.database import Base


class AuditoriaLog(Base):
    """
    Tabla de auditoría poblada exclusivamente por el trigger fn_auditoria().
    Los servicios nunca escriben aquí directamente.
    """

    __tablename__ = "auditoria_log"
    __table_args__ = (
        CheckConstraint(
            "operacion IN ('INSERT', 'UPDATE', 'DELETE')",
            name="ck_auditoria_operacion",
        ),
        Index("idx_auditoria_tabla",    "nombre_tabla"),
        Index("idx_auditoria_registro", "id_registro"),
        # fecha_accion DESC — Alembic no compara dirección de orden
        Index("idx_auditoria_fecha",    "fecha_accion"),
    )

    id_log: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre_tabla: Mapped[str] = mapped_column(String(100), nullable=False)
    operacion: Mapped[str] = mapped_column(String(10), nullable=False)
    id_registro: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    registro_anterior: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    registro_nuevo: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    usuario_accion: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    usuario_bd: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_accion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
