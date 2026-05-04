"""DTOs de autenticación."""

from typing import List
from pydantic import BaseModel, EmailStr
import uuid


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class TokenData(BaseModel):
    """Payload decodificado del JWT. Se inyecta via dependency."""
    sub: str            # id_usuario como string
    email: str
    nombre: str
    apellido: str
    rol: str
    permisos: List[str]
