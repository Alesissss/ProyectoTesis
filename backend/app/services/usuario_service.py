import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dtos.usuario_dto import (
    UsuarioCreateRequest,
    UsuarioUpdateRequest,
    UsuarioResponse,
    UsuarioListResponse,
)
from app.dtos.auth_dto import TokenData
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.utils.password_handler import hash_password


class UsuarioService:

    async def crear(
        self,
        db: AsyncSession,
        request: UsuarioCreateRequest,
        current_user: TokenData,
    ) -> UsuarioResponse:
        # Verificar email único
        existe = await db.execute(
            select(Usuario).where(Usuario.email == request.email)
        )
        if existe.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "El email ya está registrado")

        # Verificar que el rol existe
        rol = await db.get(Rol, request.id_rol)
        if not rol or not rol.estado_registro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")

        nuevo = Usuario(
            nombre=request.nombre,
            apellido=request.apellido,
            email=request.email,
            password_hash=hash_password(request.password),
            id_rol=request.id_rol,
            usuario_registro=uuid.UUID(current_user.sub),
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        await db.refresh(nuevo, ["rol"])

        return UsuarioResponse(
            id_usuario=nuevo.id_usuario,
            nombre=nuevo.nombre,
            apellido=nuevo.apellido,
            email=nuevo.email,
            id_rol=nuevo.id_rol,
            nombre_rol=nuevo.rol.nombre_rol,
            estado_registro=nuevo.estado_registro,
            fecha_registro=nuevo.fecha_registro,
        )

    async def listar(self, db: AsyncSession) -> List[UsuarioListResponse]:
        result = await db.execute(
            select(Usuario, Rol.nombre_rol)
            .join(Rol, Rol.id_rol == Usuario.id_rol)
            .where(Usuario.estado_registro == True)
            .order_by(Usuario.apellido)
        )
        filas = result.all()
        return [
            UsuarioListResponse(
                id_usuario=u.id_usuario,
                nombre=u.nombre,
                apellido=u.apellido,
                email=u.email,
                nombre_rol=nombre_rol,
                estado_registro=u.estado_registro,
            )
            for u, nombre_rol in filas
        ]

    async def obtener_por_id(self, db: AsyncSession, usuario_id: uuid.UUID) -> UsuarioResponse:
        result = await db.execute(
            select(Usuario, Rol.nombre_rol)
            .join(Rol, Rol.id_rol == Usuario.id_rol)
            .where(Usuario.id_usuario == usuario_id, Usuario.estado_registro == True)
        )
        fila = result.first()
        if not fila:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
        u, nombre_rol = fila
        return UsuarioResponse(
            id_usuario=u.id_usuario,
            nombre=u.nombre,
            apellido=u.apellido,
            email=u.email,
            id_rol=u.id_rol,
            nombre_rol=nombre_rol,
            estado_registro=u.estado_registro,
            fecha_registro=u.fecha_registro,
        )

    async def actualizar(
        self,
        db: AsyncSession,
        usuario_id: uuid.UUID,
        request: UsuarioUpdateRequest,
    ) -> UsuarioResponse:
        usuario = await db.get(Usuario, usuario_id)
        if not usuario or not usuario.estado_registro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

        if request.nombre is not None:
            usuario.nombre = request.nombre
        if request.apellido is not None:
            usuario.apellido = request.apellido
        if request.email is not None:
            usuario.email = request.email
        if request.password is not None:
            usuario.password_hash = hash_password(request.password)
        if request.id_rol is not None:
            rol = await db.get(Rol, request.id_rol)
            if not rol or not rol.estado_registro:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")
            usuario.id_rol = request.id_rol

        await db.commit()
        await db.refresh(usuario)
        return await self.obtener_por_id(db, usuario_id)

    async def deshabilitar(self, db: AsyncSession, usuario_id: uuid.UUID) -> None:
        """Soft-delete: estado_registro = False."""
        usuario = await db.get(Usuario, usuario_id)
        if not usuario or not usuario.estado_registro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
        usuario.estado_registro = False
        await db.commit()
