import uuid
from typing import List

from fastapi import APIRouter, Depends, status

from app.data.database import AuditedAsyncSession
from app.dtos.auth_dto import TokenData
from app.dtos.common_dto import ApiResponse, MensajeResponse
from app.dtos.usuario_dto import (
    UsuarioCreateRequest,
    UsuarioUpdateRequest,
    UsuarioResponse,
    UsuarioListResponse,
)
from app.services.usuario_service import UsuarioService
from app.utils.dependencies import get_current_user, get_db, require_permission

router = APIRouter()
_service = UsuarioService()


@router.get(
    "/me",
    response_model=ApiResponse[UsuarioResponse],
    summary="Mi perfil",
)
async def mi_perfil(
    current_user: TokenData = Depends(get_current_user),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[UsuarioResponse]:
    data = await _service.obtener_por_id(db, uuid.UUID(current_user.sub))
    return ApiResponse.success(data)


@router.get(
    "",
    response_model=ApiResponse[List[UsuarioListResponse]],
    summary="Listar todos los usuarios (admin)",
)
async def listar_usuarios(
    current_user: TokenData = Depends(require_permission("usuario:ver_todos")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[List[UsuarioListResponse]]:
    data = await _service.listar(db)
    return ApiResponse.success(data)


@router.post(
    "",
    response_model=ApiResponse[UsuarioResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario (admin)",
)
async def crear_usuario(
    request: UsuarioCreateRequest,
    current_user: TokenData = Depends(require_permission("usuario:gestionar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[UsuarioResponse]:
    data = await _service.crear(db, request, current_user)
    return ApiResponse.success(data)


@router.put(
    "/{usuario_id}",
    response_model=ApiResponse[UsuarioResponse],
    summary="Actualizar usuario (admin)",
)
async def actualizar_usuario(
    usuario_id: uuid.UUID,
    request: UsuarioUpdateRequest,
    current_user: TokenData = Depends(require_permission("usuario:gestionar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[UsuarioResponse]:
    data = await _service.actualizar(db, usuario_id, request)
    return ApiResponse.success(data)


@router.delete(
    "/{usuario_id}",
    response_model=ApiResponse[MensajeResponse],
    summary="Deshabilitar usuario / soft-delete (admin)",
)
async def deshabilitar_usuario(
    usuario_id: uuid.UUID,
    current_user: TokenData = Depends(require_permission("usuario:gestionar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[MensajeResponse]:
    await _service.deshabilitar(db, usuario_id)
    return ApiResponse.success(MensajeResponse(mensaje="Usuario deshabilitado correctamente"))
