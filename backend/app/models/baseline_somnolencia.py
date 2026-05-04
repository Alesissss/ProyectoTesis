import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Double, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class BaselineSomnolencia(Base, AuditMixin):
    """Baseline personal del Módulo 1 (visión, somnolencia).

    Independiente de `baselines_emg` para que la calibración de M1 (que solo
    requiere cámara) no quede bloqueada esperando hardware EMG. Lifecycle
    propio: cada usuario tiene a lo más un baseline activo a la vez.
    """

    __tablename__ = "baselines_somnolencia"
    __table_args__ = (
        Index("idx_baselines_somn_usuario", "id_usuario"),
        Index(
            "idx_baselines_somn_activo",
            "id_usuario",
            "activo",
            postgresql_where=text("activo = TRUE"),
        ),
    )

    id_baseline: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )

    # Salida del BiLSTM en estado alerta del sujeto
    p_somnolencia: Mapped[float] = mapped_column(Double, nullable=False)

    # Auxiliares para trazabilidad
    ear_promedio: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    mar_promedio: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    duracion_s: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    frames_procesados: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="baselines_somnolencia"
    )
