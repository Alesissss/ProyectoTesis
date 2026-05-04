"""Service del baseline personal M1 (somnolencia)."""

import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dtos.auth_dto import TokenData
from app.dtos.baseline_somnolencia_dto import (
    BaselineSomnolenciaCreateRequest,
    BaselineSomnolenciaResponse,
)
from app.models.baseline_somnolencia import BaselineSomnolencia


class BaselineSomnolenciaService:

    async def registrar(
        self,
        db: AsyncSession,
        request: BaselineSomnolenciaCreateRequest,
        current_user: TokenData,
    ) -> BaselineSomnolenciaResponse:
        usuario_id = uuid.UUID(current_user.sub)

        # Desactivar baselines anteriores del usuario
        await db.execute(
            update(BaselineSomnolencia)
            .where(
                BaselineSomnolencia.id_usuario == usuario_id,
                BaselineSomnolencia.activo == True,  # noqa: E712
            )
            .values(activo=False)
        )

        nuevo = BaselineSomnolencia(
            id_usuario=usuario_id,
            p_somnolencia=request.p_somnolencia,
            ear_promedio=request.ear_promedio,
            mar_promedio=request.mar_promedio,
            duracion_s=request.duracion_s,
            frames_procesados=request.frames_procesados,
            activo=True,
            usuario_registro=usuario_id,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)

        return BaselineSomnolenciaResponse.model_validate(nuevo)

    async def obtener_activo(
        self, db: AsyncSession, current_user: TokenData
    ) -> BaselineSomnolenciaResponse:
        usuario_id = uuid.UUID(current_user.sub)
        result = await db.execute(
            select(BaselineSomnolencia).where(
                BaselineSomnolencia.id_usuario == usuario_id,
                BaselineSomnolencia.activo == True,  # noqa: E712
                BaselineSomnolencia.estado_registro == True,  # noqa: E712
            )
        )
        baseline = result.scalar_one_or_none()
        if not baseline:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "No hay baseline de somnolencia activo para este usuario",
            )
        return BaselineSomnolenciaResponse.model_validate(baseline)

    async def historial(
        self, db: AsyncSession, current_user: TokenData
    ) -> List[BaselineSomnolenciaResponse]:
        usuario_id = uuid.UUID(current_user.sub)
        result = await db.execute(
            select(BaselineSomnolencia)
            .where(
                BaselineSomnolencia.id_usuario == usuario_id,
                BaselineSomnolencia.estado_registro == True,  # noqa: E712
            )
            .order_by(BaselineSomnolencia.fecha_registro.desc())
        )
        baselines = result.scalars().all()
        return [BaselineSomnolenciaResponse.model_validate(b) for b in baselines]
