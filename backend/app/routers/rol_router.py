from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.database import AuditedAsyncSession
from app.dtos.auth_dto import TokenData
from app.dtos.common_dto import ApiResponse
from app.models.rol import Rol
from app.utils.dependencies import get_db, require_permission


class RolResponse(BaseModel):
    model_config = {"from_attributes": True}
    id_rol: int
    nombre_rol: str
    descripcion: str | None = None


router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[List[RolResponse]],
    summary="Listar roles disponibles (admin)",
)
async def listar_roles(
    current_user: TokenData = Depends(require_permission("usuario:gestionar")),
    db: AuditedAsyncSession = Depends(get_db),
) -> ApiResponse[List[RolResponse]]:
    """Devuelve todos los roles activos. Usado por el panel de administración."""
    result = await db.execute(
        select(Rol)
        .where(Rol.estado_registro == True, Rol.nombre_rol != "superadmin")
        .order_by(Rol.id_rol)
    )
    data = [RolResponse.model_validate(r) for r in result.scalars().all()]
    return ApiResponse.success(data)
