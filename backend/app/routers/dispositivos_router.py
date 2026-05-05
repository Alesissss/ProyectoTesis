"""Endpoints de inspección de hardware. Por ahora solo cámaras."""
from fastapi import APIRouter, Depends, Query

from app.dtos.auth_dto import TokenData
from app.dtos.common_dto import ApiResponse
from app.dtos.dispositivos_dto import CamaraDisponibleResponse
from app.services import dispositivos_service
from app.utils.dependencies import require_permission

router = APIRouter()


@router.get(
    "/camaras",
    response_model=ApiResponse[list[CamaraDisponibleResponse]],
    summary="Listar cámaras detectadas en la unidad de procesamiento local",
)
async def listar_camaras(
    refresh: bool = Query(default=False, description="Forzar re-escaneo (ignorar caché)"),
    _user: TokenData = Depends(require_permission("evaluacion:registrar")),
) -> ApiResponse[list[CamaraDisponibleResponse]]:
    raw = await dispositivos_service.listar_camaras(force_refresh=refresh)
    data = [CamaraDisponibleResponse(**c) for c in raw]
    return ApiResponse.success(data)
