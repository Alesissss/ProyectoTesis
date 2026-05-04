"""
Dependencias reutilizables de FastAPI.

get_current_user  → extrae y valida el JWT de la cabecera Authorization
require_permission → fábrica de dependencias para chequeo de permisos atómicos
get_db            → AuditedAsyncSession con el user_id ya inyectado
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.data.database import AuditedAsyncSession, audited_session_factory
from app.dtos.auth_dto import TokenData
from app.utils.jwt_handler import decode_token

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenData:
    try:
        return decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(codigo: str):
    """
    Fábrica de dependencias: valida que el usuario tenga el permiso indicado.
    Uso en router: current_user = Depends(require_permission('evaluacion:registrar'))
    """

    async def _check(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if codigo not in current_user.permisos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere el permiso '{codigo}'",
            )
        return current_user

    return _check


async def get_db(
    current_user: TokenData = Depends(get_current_user),
) -> AsyncGenerator[AuditedAsyncSession, None]:
    """
    Sesión auditada lista para usar: el user_id ya está seteado en
    la variable de sesión de PostgreSQL para que fn_auditoria() lo lea.
    Equivale al override de SaveChangesAsync en EF Core.
    """
    async with audited_session_factory() as session:
        await session.set_audit_user(current_user.sub)
        yield session
