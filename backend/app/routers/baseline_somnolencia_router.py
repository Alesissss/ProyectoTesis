"""Endpoints CRUD del baseline personal M1 (somnolencia)."""

from typing import List

from fastapi import APIRouter, Depends, status

from app.data.database import AuditedAsyncSession
from app.dtos.auth_dto import TokenData
from app.dtos.baseline_somnolencia_dto import (
    BaselineSomnolenciaCreateRequest,
    BaselineSomnolenciaResponse,
)
from app.dtos.common_dto import ApiResponse
from app.services.baseline_somnolencia_service import BaselineSomnolenciaService
from app.utils.dependencies import get_db, require_permission

router = APIRouter()
_service = BaselineSomnolenciaService()


@router.post(
    "",
    response_model=ApiResponse[BaselineSomnolenciaResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar baseline de somnolencia (M1)",
)
async def registrar_baseline_somnolencia(
    request: BaselineSomnolenciaCreateRequest,
    current_user: TokenData = Depends(
        require_permission("baseline_somnolencia:registrar")
    ),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[BaselineSomnolenciaResponse]:
    data = await _service.registrar(db, request, current_user)
    return ApiResponse.success(data)


@router.get(
    "/activo",
    response_model=ApiResponse[BaselineSomnolenciaResponse],
    summary="Mi baseline de somnolencia activo",
)
async def mi_baseline_somnolencia_activo(
    current_user: TokenData = Depends(
        require_permission("baseline_somnolencia:ver_propios")
    ),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[BaselineSomnolenciaResponse]:
    data = await _service.obtener_activo(db, current_user)
    return ApiResponse.success(data)


@router.get(
    "/historial",
    response_model=ApiResponse[List[BaselineSomnolenciaResponse]],
    summary="Historial de mis baselines de somnolencia",
)
async def mi_historial_baselines_somnolencia(
    current_user: TokenData = Depends(
        require_permission("baseline_somnolencia:ver_propios")
    ),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[List[BaselineSomnolenciaResponse]]:
    data = await _service.historial(db, current_user)
    return ApiResponse.success(data)
