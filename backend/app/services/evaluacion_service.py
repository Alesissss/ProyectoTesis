import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dtos.evaluacion_dto import (
    EvaluacionRequest,
    EvaluacionResponse,
    EvaluacionResumenResponse,
)
from app.dtos.auth_dto import TokenData
from app.models.evaluacion import Evaluacion
from app.models.usuario import Usuario


class EvaluacionService:

    async def registrar(
        self,
        db: AsyncSession,
        request: EvaluacionRequest,
        current_user: TokenData,
    ) -> EvaluacionResponse:
        usuario_id = uuid.UUID(current_user.sub)

        # Verificar que el usuario existe y está activo
        usuario = await db.get(Usuario, usuario_id)
        if not usuario or not usuario.estado_registro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

        nueva = Evaluacion(
            id_usuario=usuario_id,
            id_baseline_usado=request.id_baseline_usado,
            p_somnolencia=request.p_somnolencia,
            p_fatiga_fisiologica=request.p_fatiga_fisiologica,
            p_total=request.p_total,
            dictamen=request.dictamen.value,
            umbral_usado=request.umbral_usado,
            features_conductuales=request.features_conductuales,
            features_emg=request.features_emg,
            features_hrv=request.features_hrv,
            metadatos=request.metadatos,
            duracion_captura_s=request.duracion_captura_s,
            usuario_registro=usuario_id,
        )
        db.add(nueva)
        await db.commit()
        await db.refresh(nueva)

        return EvaluacionResponse.model_validate(nueva)

    async def mis_evaluaciones(
        self, db: AsyncSession, current_user: TokenData
    ) -> List[EvaluacionResumenResponse]:
        usuario_id = uuid.UUID(current_user.sub)
        result = await db.execute(
            select(Evaluacion)
            .where(Evaluacion.id_usuario == usuario_id, Evaluacion.estado_registro == True)
            .order_by(Evaluacion.fecha_registro.desc())
        )
        evaluaciones = result.scalars().all()
        return [EvaluacionResumenResponse.model_validate(e) for e in evaluaciones]

    async def todas(self, db: AsyncSession) -> List[EvaluacionResumenResponse]:
        result = await db.execute(
            select(Evaluacion)
            .where(Evaluacion.estado_registro == True)
            .order_by(Evaluacion.fecha_registro.desc())
        )
        evaluaciones = result.scalars().all()
        return [EvaluacionResumenResponse.model_validate(e) for e in evaluaciones]

    async def obtener_por_id(
        self, db: AsyncSession, evaluacion_id: uuid.UUID, current_user: TokenData
    ) -> EvaluacionResponse:
        evaluacion = await db.get(Evaluacion, evaluacion_id)
        if not evaluacion or not evaluacion.estado_registro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluación no encontrada")

        # Un médico solo puede ver sus propias evaluaciones
        es_medico = current_user.rol == "medico"
        if es_medico and evaluacion.id_usuario != uuid.UUID(current_user.sub):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso denegado")

        return EvaluacionResponse.model_validate(evaluacion)
