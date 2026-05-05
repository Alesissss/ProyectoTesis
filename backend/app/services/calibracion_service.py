"""Service de calibración M1: dispara el subproceso `local/main.py --calibracion-m1`,
parsea su salida JSON, persiste el baseline y devuelve el resultado al frontend.

Riesgos manejados:
- Concurrencia (un solo médico por dispositivo embebido) → asyncio.Lock global.
- Bloqueo: subprocess async, libera el worker mientras espera.
- Timeout duro configurable (Settings.calibracion_timeout_s).
- Stdout puede traer warnings de MediaPipe → parseo busca un marcador único
  (`===CALIBRACION_RESULT===`) antes del JSON.
- Command injection: args van como lista, nunca como shell string. Cero input
  del usuario va al subprocess (token viene de la sesión autenticada).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# UTF-8 obligatorio en stdout del subprocess (Windows default cp1252).
_SUBPROCESS_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
from app.dtos.auth_dto import TokenData
from app.dtos.baseline_somnolencia_dto import (
    BaselineSomnolenciaCreateRequest,
    CalibracionIniciarRequest,
    CalibracionResultadoResponse,
)
from app.services.baseline_somnolencia_service import BaselineSomnolenciaService

logger = logging.getLogger(__name__)

# Marcador que el subproceso emite ANTES del JSON final, para separar la
# salida útil del ruido de MediaPipe / TensorFlow Lite.
RESULT_MARKER = "===CALIBRACION_RESULT==="

# Lock global: solo una calibración a la vez (la cámara es recurso único).
_calibracion_lock = asyncio.Lock()


class CalibracionService:
    def __init__(self) -> None:
        self._baseline_service = BaselineSomnolenciaService()

    async def iniciar_calibracion_m1(
        self,
        db: AsyncSession,
        request: CalibracionIniciarRequest,
        current_user: TokenData,
        bearer_token: str,
    ) -> CalibracionResultadoResponse:
        """Lanza el subproceso de calibración, parsea su salida y persiste."""

        if _calibracion_lock.locked():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya hay una calibración en curso. Espera a que termine.",
            )

        async with _calibracion_lock:
            datos_local = await self._ejecutar_subproceso(request, bearer_token)

        # Liveness: si la captura no es de un sujeto vivo, no se persiste un
        # baseline basura (que contaminaría TODAS las futuras evaluaciones).
        if datos_local.get("liveness_ok") is False:
            razones = datos_local.get("razones_liveness", [])
            mensaje = "Calibración rechazada: " + " | ".join(razones) if razones else \
                      "La calibración no superó la validación de liveness."
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, mensaje)

        # Persistir el baseline (servicio existente)
        create_req = BaselineSomnolenciaCreateRequest(
            p_somnolencia=datos_local["p_somnolencia"],
            ear_promedio=datos_local.get("ear_promedio"),
            mar_promedio=datos_local.get("mar_promedio"),
            duracion_s=datos_local.get("duracion_s"),
            frames_procesados=datos_local.get("frames_procesados"),
        )
        baseline_resp = await self._baseline_service.registrar(db, create_req, current_user)

        return CalibracionResultadoResponse(
            baseline=baseline_resp,
            duracion_real_s=datos_local.get("duracion_s", 0.0),
            frames_procesados=datos_local.get("frames_procesados", 0),
            ventanas_inferidas=datos_local.get("ventanas_inferidas", 0),
            fps_observado=datos_local.get("fps_observado"),
        )

    async def _ejecutar_subproceso(
        self,
        request: CalibracionIniciarRequest,
        bearer_token: str,
    ) -> dict:
        """Ejecuta el subproceso de captura y devuelve el dict parseado del JSON."""
        local_main = self._resolver_main_path()
        python_exe = settings.resolver_python_local()

        cmd = [
            python_exe,
            str(local_main),
            "--calibracion-m1",
            "--token", bearer_token,
            "--duracion", str(request.duracion_s),
        ]
        if request.camera_profile:
            cmd.extend(["--camera-profile", request.camera_profile])
        if request.camara_id is not None:
            cmd.extend(["--camara", str(request.camara_id)])

        logger.info("Disparando subproceso de calibración: %s", " ".join(cmd[:3]))

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
                timeout=settings.calibracion_timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                f"La calibración excedió {settings.calibracion_timeout_s} s.",
            )
        except FileNotFoundError as exc:
            logger.exception("No se encontró el script local de calibración")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"No se encontró el script de captura: {exc}",
            )

        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")

        if completed.returncode != 0:
            logger.error("Subproceso falló (code=%s). stderr=%s", completed.returncode, stderr[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"La captura falló (código {completed.returncode}). "
                f"Detalle: {stderr.strip().splitlines()[-1] if stderr.strip() else 'sin detalle'}",
            )

        # Buscar el marcador y parsear el JSON que viene después
        idx = stdout.rfind(RESULT_MARKER)
        if idx < 0:
            logger.error("Marcador %s no encontrado en stdout. Salida: %s",
                         RESULT_MARKER, stdout[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "El subproceso no emitió el resultado de calibración esperado.",
            )

        json_str = stdout[idx + len(RESULT_MARKER):].strip()
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.exception("JSON malformado en salida del subproceso")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Resultado de calibración malformado: {exc}",
            )

        # Liveness fail: el subprocess emite el dict sin p_somnolencia. Es
        # válido — la captura se rechazó antes de inferir. Devolvemos el dict
        # tal cual; el caller lo traduce a HTTP 422.
        if data.get("liveness_ok") is False:
            return data

        if "p_somnolencia" not in data:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Resultado de calibración incompleto (falta p_somnolencia).",
            )
        return data

    def _resolver_main_path(self) -> Path:
        """Resuelve la ruta absoluta a `local/main.py`."""
        configured = Path(settings.local_main_path)
        if configured.is_absolute():
            return configured
        # Relativa al directorio de trabajo del backend
        backend_dir = Path(__file__).resolve().parents[2]
        return (backend_dir / configured).resolve()
