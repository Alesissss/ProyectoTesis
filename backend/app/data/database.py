"""
Conexión asíncrona a PostgreSQL via SQLAlchemy.

AuditedAsyncSession es el equivalente del SaveChangesAsync override de EF Core:
antes de cualquier flush/commit, inyecta el UUID del usuario autenticado
como variable de sesión de PostgreSQL ('app.current_user_id').
El trigger fn_auditoria() la lee con current_setting() para poblar usuario_accion
en auditoria_log sin que los servicios lo gestionen manualmente.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings


# ── Motor asíncrono ───────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)


# ── Base declarativa (todas las entidades heredan de aquí) ────────────────────
class Base(DeclarativeBase):
    pass


# ── Session auditada (equivalente a SaveChangesAsync override) ────────────────
class AuditedAsyncSession(AsyncSession):
    """
    AsyncSession con soporte de auditoría a nivel de BD.
    Llama a set_config() en cada transacción para que el trigger
    fn_auditoria() pueda registrar qué usuario de aplicación realizó
    la operación, sin necesidad de código en cada servicio.
    """

    async def set_audit_user(self, user_id: Optional[str]) -> None:
        uid = str(user_id) if user_id else ""
        await self.execute(
            text("SELECT set_config('app.current_user_id', :uid, TRUE)"),
            {"uid": uid},
        )


# ── Fábricas de sesión ────────────────────────────────────────────────────────
# Sesión sin auditoría (para login u operaciones anónimas)
plain_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Sesión auditada (para operaciones autenticadas)
audited_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AuditedAsyncSession,
)


# ── Dependencias FastAPI ──────────────────────────────────────────────────────
async def get_plain_db() -> AsyncGenerator[AsyncSession, None]:
    """Para endpoints sin autenticación (ej. /auth/login)."""
    async with plain_session_factory() as session:
        yield session


async def get_audited_db() -> AsyncGenerator[AuditedAsyncSession, None]:
    """Para endpoints autenticados. El router inyecta el user_id después."""
    async with audited_session_factory() as session:
        yield session
