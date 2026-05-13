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
        """Dispara `local/main.py` por subprocess (con --no-post), recibe el
        payload de evaluación calculado y lo persiste él mismo. Single source
        of truth: el subprocess solo computa; la BD la toca exclusivamente
        este service.
        """
        if _evaluacion_lock.locked():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya se está realizando una evaluación en este momento. "
                "Espera a que termine antes de iniciar otra.",
            )

        async with _evaluacion_lock:
            datos = await self._ejecutar_subproceso(request, bearer_token)

        # ── Liveness: el subproceso rechaza la captura ANTES de calcular ─────
        # Si el local detectó cámara apuntando a la nada, foto estática, o
        # señal rPPG sin perfusión, NO hay evaluación en BD: traducimos a 422.
        if datos.get("liveness_ok") is False:
            razones = datos.get("razones_liveness", [])
            mensaje = (
                "Captura inválida: " + " | ".join(razones)
                if razones
                else "No se detectó al sujeto frente a la cámara durante la captura. "
                     "Verifica iluminación, posición y reintenta."
            )
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, mensaje)

        # ── Persistir la evaluación a partir del payload del subprocess ──────
        payload_eval = datos.get("payload_evaluacion")
        if not isinstance(payload_eval, dict):
            logger.error("Subprocess no devolvió payload_evaluacion: %s", datos)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "La captura no produjo datos completos para registrar la evaluación. "
                "Reintenta.",
            )

        try:
            request_dto = EvaluacionRequest.model_validate(payload_eval)
        except Exception:
            logger.exception("Payload de evaluación inválido: %s", payload_eval)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Los datos de la evaluación no superaron la validación. "
                "Reintenta la captura.",
            )

        evaluacion_resp = await self.registrar(db, request_dto, current_user)
        evaluacion = await db.get(Evaluacion, evaluacion_resp.id_evaluacion)
        if not evaluacion:
            logger.error("Persistencia exitosa pero no se halla la evaluación recién creada")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "La evaluación se procesó pero no se encontró en la base de datos. "
                "Contacta al administrador.",
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
            "--no-post",  # el backend persiste; el subprocess solo computa.
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
                "La evaluación tardó más de lo esperado y se canceló. "
                "Verifica la conexión de la cámara e intenta nuevamente.",
            )
        except FileNotFoundError as exc:
            logger.exception("No se encontró el script local de evaluación: %s", exc)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "No fue posible iniciar la captura. "
                "Contacta al administrador del sistema.",
            )

        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")

        if completed.returncode != 0:
            logger.error("Subproceso de evaluación falló (code=%s). stderr=%s",
                         completed.returncode, stderr[-2000:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Ocurrió un problema durante la captura. "
                "Verifica la cámara y el Arduino, y reintenta.",
            )

        idx = stdout.rfind(EVALUACION_RESULT_MARKER)
        if idx < 0:
            logger.error("Marcador %s no encontrado en stdout. stderr=%s. stdout-tail=%s",
                         EVALUACION_RESULT_MARKER, stderr[-1000:], stdout[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "La captura no produjo un resultado válido. "
                "Reintenta verificando la cámara.",
            )

        json_str = stdout[idx + len(EVALUACION_RESULT_MARKER):].strip()
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.exception("JSON malformado en salida del subproceso. stdout-tail=%s",
                             stdout[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "El resultado de la evaluación no se pudo interpretar. "
                "Reintenta la captura.",
            )
        return data

    def _resolver_main_path(self) -> Path:
        """Resuelve la ruta absoluta a `local/main.py` (mismo helper que CalibracionService)."""
        configured = Path(settings.local_main_path)
        if configured.is_absolute():
            return configured
        backend_dir = Path(__file__).resolve().parents[2]
        return (backend_dir / configured).resolve()
