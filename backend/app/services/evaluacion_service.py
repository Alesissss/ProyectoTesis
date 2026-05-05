import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# UTF-8 obligatorio para stdout del subprocess (mismo problema que en
# dispositivos_service.py — Windows default cp1252 corrompe el JSON final
# si tiene caracteres no-ASCII).
_SUBPROCESS_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
from app.dtos.evaluacion_dto import (
    EvaluacionIniciarRequest,
    EvaluacionIniciarResultado,
    EvaluacionRequest,
    EvaluacionResponse,
    EvaluacionResumenResponse,
)
from app.dtos.auth_dto import TokenData
from app.models.evaluacion import Evaluacion
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

# Marcador único que el subproceso emite ANTES del JSON final, para separar
# la salida útil del ruido de MediaPipe / TensorFlow Lite / Torch.
EVALUACION_RESULT_MARKER = "===EVALUACION_RESULT==="

# Lock global: solo una evaluación a la vez (cámara y puerto Arduino son
# recursos únicos en la "unidad de procesamiento local").
_evaluacion_lock = asyncio.Lock()


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

    # ── Evaluación automatizada vía subprocess ────────────────────────────────

    async def iniciar_evaluacion(
        self,
        db: AsyncSession,
        request: EvaluacionIniciarRequest,
        current_user: TokenData,
        bearer_token: str,
    ) -> EvaluacionIniciarResultado:
        """Dispara `local/main.py` por subprocess, espera su salida JSON con
        el id de la evaluación recién creada, y devuelve la evaluación
        completa al frontend.

        Mismo patrón que CalibracionService.iniciar_calibracion_m1, pero el
        backend NO re-registra la evaluación: el script local ya la POSTea
        a `/evaluaciones` con su propio token y el backend solo la lee.
        """
        if _evaluacion_lock.locked():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya hay una evaluación en curso. Espera a que termine.",
            )

        async with _evaluacion_lock:
            datos = await self._ejecutar_subproceso(request, bearer_token)

        # ── Liveness: el subproceso rechaza la captura ANTES de POSTear ──────
        # Si el local detectó cámara apuntando a la nada, foto estática, o
        # señal rPPG sin perfusión, NO hay evaluación en BD: traducimos a 422.
        if datos.get("liveness_ok") is False:
            razones = datos.get("razones_liveness", [])
            mensaje = "Captura inválida: " + " | ".join(razones) if razones else \
                      "La captura no superó la validación de liveness."
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, mensaje)

        # El subprocess incluye `id_evaluacion` en el JSON tras POST exitoso.
        id_eval_str = datos.get("id_evaluacion")
        if not id_eval_str:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "El script local completó la captura pero no pudo registrar la "
                "evaluación en el backend. Revisar logs del subproceso.",
            )
        try:
            id_eval = uuid.UUID(id_eval_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"id_evaluacion inválido devuelto por el subproceso: {id_eval_str!r}",
            )

        evaluacion = await db.get(Evaluacion, id_eval)
        if not evaluacion:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "La evaluación reportada por el subproceso no existe en la BD.",
            )

        return EvaluacionIniciarResultado(
            evaluacion=EvaluacionResponse.model_validate(evaluacion),
            duracion_real_s=float(datos.get("duracion_real_s", 0.0)),
            frames_procesados=int(datos.get("frames_procesados", 0)),
            fps_observado=datos.get("fps_observado"),
            n_muestras_emg=int(datos.get("n_muestras_emg", 0)),
            hrv_disponible=bool(datos.get("hrv_disponible", False)),
            justificacion=list(datos.get("justificacion", [])),
        )

    async def _ejecutar_subproceso(
        self,
        request: EvaluacionIniciarRequest,
        bearer_token: str,
    ) -> dict:
        """Ejecuta `local/main.py` y parsea el JSON tras EVALUACION_RESULT_MARKER."""
        local_main = self._resolver_main_path()
        python_exe = settings.resolver_python_local()

        cmd = [
            python_exe,
            str(local_main),
            "--token", bearer_token,
            "--duracion", str(request.duracion_s),
        ]
        if request.camera_profile:
            cmd.extend(["--camera-profile", request.camera_profile])
        if request.camara_id is not None:
            cmd.extend(["--camara", str(request.camara_id)])
        if request.puerto_arduino:
            cmd.extend(["--puerto", request.puerto_arduino])

        logger.info("Disparando subproceso de evaluación: %s ...", " ".join(cmd[:3]))

        # subprocess.run síncrono dentro de to_thread: evita el NotImplementedError
        # que tira asyncio.create_subprocess_exec cuando uvicorn corre con
        # SelectorEventLoop en Windows. Ver feedback_subprocess_loop.md.
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                cmd,
                cwd=str(local_main.parent),
                env=_SUBPROCESS_ENV,
                capture_output=True,
                timeout=settings.evaluacion_timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                f"La evaluación excedió {settings.evaluacion_timeout_s} s.",
            )
        except FileNotFoundError as exc:
            logger.exception("No se encontró el script local de evaluación")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"No se encontró el script de captura: {exc}",
            )

        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")

        if completed.returncode != 0:
            logger.error("Subproceso de evaluación falló (code=%s). stderr=%s",
                         completed.returncode, stderr[-500:])
            ultimo = stderr.strip().splitlines()[-1] if stderr.strip() else "sin detalle"
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"La captura falló (código {completed.returncode}). Detalle: {ultimo}",
            )

        idx = stdout.rfind(EVALUACION_RESULT_MARKER)
        if idx < 0:
            logger.error("Marcador %s no encontrado en stdout. Salida: %s",
                         EVALUACION_RESULT_MARKER, stdout[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "El subproceso no emitió el resultado de evaluación esperado.",
            )

        json_str = stdout[idx + len(EVALUACION_RESULT_MARKER):].strip()
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.exception("JSON malformado en salida del subproceso")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Resultado de evaluación malformado: {exc}",
            )
        return data

    def _resolver_main_path(self) -> Path:
        """Resuelve la ruta absoluta a `local/main.py` (mismo helper que CalibracionService)."""
        configured = Path(settings.local_main_path)
        if configured.is_absolute():
            return configured
        backend_dir = Path(__file__).resolve().parents[2]
        return (backend_dir / configured).resolve()
