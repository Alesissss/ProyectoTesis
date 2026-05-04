from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dtos.auth_dto import LoginRequest, TokenResponse
from app.models.usuario import Usuario
from app.models.rol_permiso import RolPermiso
from app.models.permiso import Permiso
from app.utils.password_handler import verify_password
from app.utils.jwt_handler import create_access_token
from app.config import settings


class AuthService:

    async def login(self, db: AsyncSession, request: LoginRequest) -> TokenResponse:
        # Carga el usuario con su rol (necesario para leer nombre_rol)
        result = await db.execute(
            select(Usuario)
            .where(Usuario.email == request.email, Usuario.estado_registro == True)
            .options(selectinload(Usuario.rol))
        )
        usuario = result.scalar_one_or_none()

        if not usuario or not verify_password(request.password, usuario.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )

        # Query separada: permisos activos asignados al rol del usuario
        permisos_result = await db.execute(
            select(Permiso.codigo_permiso)
            .join(RolPermiso, RolPermiso.id_permiso == Permiso.id_permiso)
            .where(
                RolPermiso.id_rol == usuario.id_rol,
                RolPermiso.estado_registro == True,
                Permiso.estado_registro == True,
            )
        )
        permisos = [row[0] for row in permisos_result.all()]

        token = create_access_token(
            user_id=str(usuario.id_usuario),
            email=usuario.email,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            rol=usuario.rol.nombre_rol,
            permisos=permisos,
        )

        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_expire_minutes * 60,
        )
