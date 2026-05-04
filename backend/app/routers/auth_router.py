from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.database import get_plain_db
from app.dtos.auth_dto import LoginRequest, TokenResponse
from app.dtos.common_dto import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter()
_service = AuthService()


@router.post("/login", response_model=ApiResponse[TokenResponse], summary="Iniciar sesión")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_plain_db),
) -> ApiResponse[TokenResponse]:
    """Autentica un usuario y devuelve un JWT válido por 60 minutos."""
    data = await _service.login(db, request)
    return ApiResponse.success(data)
