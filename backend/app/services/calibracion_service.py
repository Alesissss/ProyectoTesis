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
from app.dtos.baseline_dto import BaselineCreateRequest
from app.dtos.baseline_somnolencia_dto import (
    BaselineM2Resumen,
    BaselineSomnolenciaCreateRequest,
    CalibracionIniciarRequest,
    CalibracionResultadoResponse,
)
from app.services.baseline_service import BaselineService
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
        self._baseline_m2_service = BaselineService()

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
                "Ya se está realizando una calibración en este momento. "
                "Espera a que termine antes de iniciar otra.",
            )

        async with _calibracion_lock:
            datos_local = await self._ejecutar_subproceso(request, bearer_token)

        # Liveness: si la captura no es de un sujeto vivo, no se persiste un
        # baseline basura (que contaminaría TODAS las futuras evaluaciones).
        if datos_local.get("liveness_ok") is False:
            razones = datos_local.get("razones_liveness", [])
            mensaje = (
                "Calibración rechazada: " + " | ".join(razones)
                if razones
                else "No se pudo validar que estés frente a la cámara. "
                     "Acomódate frente al lente y reintenta."
            )
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, mensaje)

        # ── Persistir baseline M1 (visión) ──────────────────────────────────
        m1 = datos_local.get("m1", {})
        create_req_m1 = BaselineSomnolenciaCreateRequest(
            p_somnolencia=m1["p_somnolencia"],
            ear_promedio=m1.get("ear_promedio"),
            mar_promedio=m1.get("mar_promedio"),
            duracion_s=m1.get("duracion_s"),
            frames_procesados=m1.get("frames_procesados"),
        )
        baseline_m1_resp = await self._baseline_service.registrar(
            db, create_req_m1, current_user
        )

        # ── Persistir baseline M2 (EMG + HRV) si la señal EMG fue válida ────
        # El schema de baselines_emg requiere rms_emg NOT NULL. Si no hubo
        # Arduino o el EMG estaba contaminado por 60 Hz, no se registra M2 y
        # se devuelve el resumen con valido=False para que la UI lo explique.
        m2 = datos_local.get("m2", {}) or {}
        emg = m2.get("emg")
        hrv = m2.get("hrv")
        calidad = m2.get("emg_calidad") or {}
        resumen_m2 = BaselineM2Resumen(
            emg_valido=bool(calidad.get("valido", False)),
            emg_ratio_60hz=calidad.get("ratio_60hz"),
            emg_motivo=calidad.get("motivo"),
            arduino_detectado=bool(m2.get("arduino_detectado", False)),
            n_muestras_emg=int(m2.get("n_muestras_emg", 0)),
        )
        if isinstance(emg, dict):
            try:
                create_req_m2 = BaselineCreateRequest(
                    rms_emg=emg["rms_emg"],
                    freq_mediana=emg["freq_mediana"],
                    freq_media=emg["freq_media"],
                    sdnn=(hrv or {}).get("sdnn"),
                    rmssd=(hrv or {}).get("rmssd"),
                    pnn50=(hrv or {}).get("pnn50"),
                )
                baseline_m2_resp = await self._baseline_m2_service.registrar(
                    db, create_req_m2, current_user
                )
                resumen_m2.id_baseline = baseline_m2_resp.id_baseline
                resumen_m2.rms_emg = baseline_m2_resp.rms_emg
                resumen_m2.freq_mediana = baseline_m2_resp.freq_mediana
                resumen_m2.freq_media = baseline_m2_resp.freq_media
                resumen_m2.sdnn = baseline_m2_resp.sdnn
                resumen_m2.rmssd = baseline_m2_resp.rmssd
                resumen_m2.pnn50 = baseline_m2_resp.pnn50
            except Exception:
                logger.exception("Fallo al persistir baseline M2; se devuelve solo M1")

        return CalibracionResultadoResponse(
            baseline=baseline_m1_resp,
            baseline_m2=resumen_m2,
            duracion_real_s=m1.get("duracion_s", 0.0),
            frames_procesados=m1.get("frames_procesados", 0),
            ventanas_inferidas=m1.get("ventanas_inferidas", 0),
            fps_observado=m1.get("fps_observado"),
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
            "--no-post",  # el backend persiste; el subprocess solo computa.
            "--token", bearer_token,
            "--duracion", str(request.duracion_s),
        ]
        if request.camera_profile:
            cmd.extend(["--camera-profile", request.camera_profile])
        if request.camara_id is not None:
            cmd.extend(["--camara", str(request.camara_id)])
        if getattr(request, "puerto_arduino", None):
            cmd.extend(["--puerto", request.puerto_arduino])

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
                "La calibración tardó más de lo esperado y se canceló. "
                "Verifica que la cámara responda correctamente e intenta de nuevo.",
            )
        except FileNotFoundError as exc:
            logger.exception("No se encontró el script local de calibración: %s", exc)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "No fue posible iniciar el proceso de captura. "
                "Contacta al administrador del sistema.",
            )

        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")

        if completed.returncode != 0:
            logger.error("Subproceso de calibración falló (code=%s). stderr=%s",
                         completed.returncode, stderr[-2000:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Ocurrió un problema durante la captura. "
                "Verifica que la cámara esté conectada e intenta nuevamente.",
            )

        # Buscar el marcador y parsear el JSON que viene después
        idx = stdout.rfind(RESULT_MARKER)
        if idx < 0:
            logger.error("Marcador %s no encontrado en stdout. stderr=%s. stdout-tail=%s",
                         RESULT_MARKER, stderr[-1000:], stdout[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "La captura no produjo un resultado válido. "
                "Verifica la cámara e intenta nuevamente.",
            )

        json_str = stdout[idx + len(RESULT_MARKER):].strip()
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.exception("JSON malformado en salida del subproceso. stdout-tail=%s",
                             stdout[-500:])
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "El resultado de la calibración no se pudo interpretar. "
                "Reintenta la captura.",
            )

        # Liveness fail: el subprocess emite el dict sin p_somnolencia. Es
        # válido — la captura se rechazó antes de inferir. Devolvemos el dict
        # tal cual; el caller lo traduce a HTTP 422.
        if data.get("liveness_ok") is False:
            return data

        # Estructura nueva: {m1: {...}, m2: {...}}. La validez se mide por la
        # presencia de m1.p_somnolencia.
        if not isinstance(data.get("m1"), dict) or "p_somnolencia" not in data["m1"]:
            logger.error("Resultado de calibración incompleto: %s", data)
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "La calibración no produjo resultados completos. "
                "Vuelve a intentarlo asegurándote de mantener el rostro visible.",
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
