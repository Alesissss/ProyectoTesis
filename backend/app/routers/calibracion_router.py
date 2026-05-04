"""Router de calibración: dispara la captura local desde un click en React."""

from fastapi import APIRouter, Depends, Header, status

from app.data.database import AuditedAsyncSession
from app.dtos.auth_dto import TokenData
from app.dtos.baseline_somnolencia_dto import (
    CalibracionIniciarRequest,
    CalibracionResultadoResponse,
)
from app.dtos.common_dto import ApiResponse
from app.services.calibracion_service import CalibracionService
from app.utils.dependencies import get_db, require_permission

router = APIRouter()
_service = CalibracionService()


@router.post(
    "/somnolencia/iniciar",
    response_model=ApiResponse[CalibracionResultadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Iniciar calibración M1 (subprocess local) y registrar baseline",
)
async def iniciar_calibracion_m1(
    request: CalibracionIniciarRequest,
    authorization: str = Header(...),
    current_user: TokenData = Depends(
        require_permission("baseline_somnolencia:registrar")
    ),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[CalibracionResultadoResponse]:
    """Lanza `local/main.py --calibracion-m1` como subproceso, espera el
    JSON con el baseline obtenido, lo persiste y devuelve el resumen.

    El JWT se reenvía al subproceso vía CLI (no por env) para que el script
    local pueda autenticar su propio POST a `/baselines/somnolencia` si
    fuese necesario; en el flujo actual, el backend persiste directamente.
    """
    bearer = authorization.removeprefix("Bearer ").strip()
    data = await _service.iniciar_calibracion_m1(db, request, current_user, bearer)
    return ApiResponse.success(data)
