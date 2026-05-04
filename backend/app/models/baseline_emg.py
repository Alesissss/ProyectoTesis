import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Double, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class BaselineEmg(Base, AuditMixin):
    __tablename__ = "baselines_emg"
    __table_args__ = (
        Index("idx_baselines_usuario", "id_usuario"),
        # Índice parcial: solo los baselines activos (equivale al WHERE activo = TRUE del DDL)
        Index(
            "idx_baselines_activo",
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

    # Features EMG
    rms_emg: Mapped[float] = mapped_column(Double, nullable=False)
    freq_mediana: Mapped[float] = mapped_column(Double, nullable=False)
    freq_media: Mapped[float] = mapped_column(Double, nullable=False)

    # Features HRV
    sdnn: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rmssd: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    pnn50: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # TRUE = baseline vigente; FALSE = histórico
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Relación
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="baselines")
