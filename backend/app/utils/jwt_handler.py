from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from jose import JWTError, jwt

from app.config import settings
from app.dtos.auth_dto import TokenData


def create_access_token(
    user_id: str,
    email: str,
    nombre: str,
    apellido: str,
    rol: str,
    permisos: List[str],
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "nombre": nombre,
        "apellido": apellido,
        "rol": rol,
        "permisos": permisos,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenData(**payload)
    except JWTError as exc:
        raise ValueError("Token inválido o expirado") from exc
