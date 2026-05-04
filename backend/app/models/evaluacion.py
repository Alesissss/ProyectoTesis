import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, Double, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.baseline_emg import BaselineEmg


class Evaluacion(Base, AuditMixin):
    __tablename__ = "evaluaciones"
    __table_args__ = (
        CheckConstraint("dictamen IN ('APTO', 'ATENCION', 'NO_APTO')", name="ck_evaluacion_dictamen"),
        CheckConstraint("p_somnolencia BETWEEN 0.0 AND 1.0",           name="ck_p_somnolencia"),
        CheckConstraint("p_fatiga_fisiologica BETWEEN 0.0 AND 1.0",    name="ck_p_fatiga"),
        CheckConstraint("p_total BETWEEN 0.0 AND 1.0",                 name="ck_p_total"),
        Index("idx_evaluaciones_usuario", "id_usuario"),
        Index("idx_evaluaciones_dictamen", "dictamen"),
        # fecha_registro DESC — Alembic no compara dirección de orden; el nombre es suficiente
        Index("idx_evaluaciones_fecha", "fecha_registro"),
    )

    id_evaluacion: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )
    id_baseline_usado: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("baselines_emg.id_baseline", ondelete="SET NULL"),
        nullable=True,
    )

    # Módulo 1 — visión conductual
    p_somnolencia: Mapped[float] = mapped_column(Double, nullable=False)
    # Módulo 2 — fisiológico
    p_fatiga_fisiologica: Mapped[float] = mapped_column(Double, nullable=False)
    # Módulo 3 — fusión tardía
    p_total: Mapped[float] = mapped_column(Double, nullable=False)
    dictamen: Mapped[str] = mapped_column(String(20), nullable=False)
    umbral_usado: Mapped[float] = mapped_column(
        Double, nullable=False, default=0.50, server_default="0.50"
    )

    # Features crudas enviadas por el script local (schema libre)
    features_conductuales: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    features_emg: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    features_hrv: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metadatos: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    duracion_captura_s: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="evaluaciones")
    baseline_usado: Mapped[Optional["BaselineEmg"]] = relationship("BaselineEmg")
