import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dtos.baseline_dto import BaselineCreateRequest, BaselineResponse
from app.dtos.auth_dto import TokenData
from app.models.baseline_emg import BaselineEmg


class BaselineService:

    async def registrar(
        self,
        db: AsyncSession,
        request: BaselineCreateRequest,
        current_user: TokenData,
    ) -> BaselineResponse:
        usuario_id = uuid.UUID(current_user.sub)

        # Desactivar todos los baselines anteriores del usuario
        await db.execute(
            update(BaselineEmg)
            .where(BaselineEmg.id_usuario == usuario_id, BaselineEmg.activo == True)
            .values(activo=False)
        )

        nuevo = BaselineEmg(
            id_usuario=usuario_id,
            rms_emg=request.rms_emg,
            freq_mediana=request.freq_mediana,
            freq_media=request.freq_media,
            sdnn=request.sdnn,
            rmssd=request.rmssd,
            pnn50=request.pnn50,
            activo=True,
            usuario_registro=usuario_id,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)

        return BaselineResponse.model_validate(nuevo)

    async def obtener_activo(
        self, db: AsyncSession, current_user: TokenData
    ) -> BaselineResponse:
        usuario_id = uuid.UUID(current_user.sub)
        result = await db.execute(
            select(BaselineEmg).where(
                BaselineEmg.id_usuario == usuario_id,
                BaselineEmg.activo == True,
                BaselineEmg.estado_registro == True,
            )
        )
        baseline = result.scalar_one_or_none()
        if not baseline:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay baseline activo para este usuario")
        return BaselineResponse.model_validate(baseline)

    async def historial(
        self, db: AsyncSession, current_user: TokenData
    ) -> List[BaselineResponse]:
        usuario_id = uuid.UUID(current_user.sub)
        result = await db.execute(
            select(BaselineEmg)
            .where(BaselineEmg.id_usuario == usuario_id, BaselineEmg.estado_registro == True)
            .order_by(BaselineEmg.fecha_registro.desc())
        )
        baselines = result.scalars().all()
        return [BaselineResponse.model_validate(b) for b in baselines]
