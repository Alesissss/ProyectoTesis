import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, status

from app.data.database import AuditedAsyncSession
from app.dtos.auth_dto import TokenData
from app.dtos.common_dto import ApiResponse
from app.dtos.evaluacion_dto import (
    EvaluacionIniciarRequest,
    EvaluacionIniciarResultado,
    EvaluacionRequest,
    EvaluacionResponse,
    EvaluacionResumenResponse,
)
from app.services.evaluacion_service import EvaluacionService
from app.utils.dependencies import get_db, require_permission

router = APIRouter()
_service = EvaluacionService()


@router.post(
    "",
    response_model=ApiResponse[EvaluacionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar evaluación (desde script local)",
)
async def registrar_evaluacion(
    request: EvaluacionRequest,
    current_user: TokenData = Depends(require_permission("evaluacion:registrar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[EvaluacionResponse]:
    """
    Endpoint llamado por el script Python local tras procesar video + EMG.
    El backend NO realiza ningún cálculo; solo valida el JSON y lo persiste.
    """
    data = await _service.registrar(db, request, current_user)
    return ApiResponse.success(data)


@router.post(
    "/iniciar",
    response_model=ApiResponse[EvaluacionIniciarResultado],
    status_code=status.HTTP_200_OK,
    summary="Iniciar evaluación completa (subprocess local) y devolver el dictamen",
)
async def iniciar_evaluacion(
    request: EvaluacionIniciarRequest,
    authorization: str = Header(...),
    current_user: TokenData = Depends(require_permission("evaluacion:registrar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[EvaluacionIniciarResultado]:
    """Lanza `local/main.py` como subproceso, espera el JSON con el id de la
    evaluación recién registrada y devuelve el dictamen al frontend para
    renderizar el semáforo APTO/ATENCIÓN/NO_APTO sin que el médico vea consola.

    Mismo patrón que `POST /calibracion/somnolencia/iniciar`.
    """
    bearer = authorization.removeprefix("Bearer ").strip()
    data = await _service.iniciar_evaluacion(db, request, current_user, bearer)
    return ApiResponse.success(data)


@router.get(
    "/mis-evaluaciones",
    response_model=ApiResponse[List[EvaluacionResumenResponse]],
    summary="Historial de mis evaluaciones (médico)",
)
async def mis_evaluaciones(
    current_user: TokenData = Depends(require_permission("evaluacion:ver_propias")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[List[EvaluacionResumenResponse]]:
    data = await _service.mis_evaluaciones(db, current_user)
    return ApiResponse.success(data)


@router.get(
    "",
    response_model=ApiResponse[List[EvaluacionResumenResponse]],
    summary="Todas las evaluaciones (admin)",
)
async def todas_las_evaluaciones(
    current_user: TokenData = Depends(require_permission("evaluacion:ver_todas")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[List[EvaluacionResumenResponse]]:
    data = await _service.todas(db)
    return ApiResponse.success(data)


@router.get(
    "/{evaluacion_id}",
    response_model=ApiResponse[EvaluacionResponse],
    summary="Detalle de una evaluación",
)
async def detalle_evaluacion(
    evaluacion_id: uuid.UUID,
    current_user: TokenData = Depends(require_permission("evaluacion:ver_propias")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[EvaluacionResponse]:
    data = await _service.obtener_por_id(db, evaluacion_id, current_user)
    return ApiResponse.success(data)
