from typing import List

from fastapi import APIRouter, Depends, status

from app.data.database import AuditedAsyncSession
from app.dtos.auth_dto import TokenData
from app.dtos.baseline_dto import BaselineCreateRequest, BaselineResponse
from app.dtos.common_dto import ApiResponse
from app.services.baseline_service import BaselineService
from app.utils.dependencies import get_db, require_permission

router = APIRouter()
_service = BaselineService()


@router.post(
    "",
    response_model=ApiResponse[BaselineResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nueva calibración EMG",
)
async def registrar_baseline(
    request: BaselineCreateRequest,
    current_user: TokenData = Depends(require_permission("baseline:registrar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[BaselineResponse]:
    """
    Registra un nuevo baseline y desactiva el anterior.
    El script local llama a este endpoint durante la fase de calibración inicial.
    """
    data = await _service.registrar(db, request, current_user)
    return ApiResponse.success(data)


@router.get(
    "/activo",
    response_model=ApiResponse[BaselineResponse],
    summary="Obtener mi baseline activo",
)
async def mi_baseline_activo(
    current_user: TokenData = Depends(require_permission("baseline:ver_propios")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[BaselineResponse]:
    data = await _service.obtener_activo(db, current_user)
    return ApiResponse.success(data)


@router.get(
    "/historial",
    response_model=ApiResponse[List[BaselineResponse]],
    summary="Historial de mis baselines",
)
async def mi_historial_baselines(
    current_user: TokenData = Depends(require_permission("baseline:ver_propios")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[List[BaselineResponse]]:
    data = await _service.historial(db, current_user)
    return ApiResponse.success(data)
