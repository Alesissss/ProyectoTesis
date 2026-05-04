"""DTOs de usuarios."""

from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime


class UsuarioCreateRequest(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    id_rol: int


class UsuarioUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    id_rol: Optional[int] = None
    password: Optional[str] = None


class UsuarioResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_usuario: uuid.UUID
    nombre: str
    apellido: str
    email: str
    id_rol: int
    nombre_rol: str
    estado_registro: bool
    fecha_registro: datetime


class UsuarioListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_usuario: uuid.UUID
    nombre: str
    apellido: str
    email: str
    nombre_rol: str
    estado_registro: bool
