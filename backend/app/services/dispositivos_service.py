"""Service para inspeccionar el hardware visible al subproceso local.

Por ahora expone solo el listado de cámaras: invoca `local/main.py
--listar-camaras`, parsea su salida y la cachea en memoria con TTL para
no pagar el costo de re-escaneo (DSHOW + MSMF abriendo índices) en cada
recarga del frontend.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings

# Fuerza UTF-8 en stdout/stderr del subprocess en Windows. Sin esto, Python
# usa cp1252 por defecto y los caracteres no-ASCII (em-dashes, acentos en
# logs de MediaPipe, etc.) llegan al backend como `�` (REPLACEMENT
# CHARACTER), corrompiendo los labels que se muestran al usuario.
_SUBPROCESS_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

logger = logging.getLogger(__name__)

CAMARAS_RESULT_MARKER = "===CAMARAS_RESULT==="

_lock = asyncio.Lock()
_cache: tuple[float, list[dict]] | None = None  # (timestamp, payload)


def _resolver_main_path() -> Path:
    configured = Path(settings.local_main_path)
    if configured.is_absolute():
        return configured
    backend_dir = Path(__file__).resolve().parents[2]
    return (backend_dir / configured).resolve()


async def listar_camaras(force_refresh: bool = False) -> list[dict]:
    """Devuelve la lista de cámaras detectadas. Usa caché TTL por defecto."""
    global _cache

    if not force_refresh and _cache is not None:
        ts, payload = _cache
        if time.time() - ts < settings.camaras_cache_ttl_s:
            return payload

    # Serializar — un único scan a la vez (la cámara es recurso compartido).
    async with _lock:
        # Re-check tras adquirir lock (otra request pudo refrescar).
        if not force_refresh and _cache is not None:
            ts, payload = _cache
            if time.time() - ts < settings.camaras_cache_ttl_s:
                return payload

        payload = await _scan_subproceso()
        _cache = (time.time(), payload)
        return payload


def _scan_blocking(cmd: list[str], cwd: str, timeout_s: int) -> subprocess.CompletedProcess:
    """Ejecuta el subprocess de forma SÍNCRONA. Se invoca dentro de un thread
    vía `asyncio.to_thread` para no bloquear el event loop. Usar la API
    síncrona evita el `NotImplementedError` que tira `asyncio.create_subprocess_exec`
    cuando uvicorn corre con SelectorEventLoop en Windows (con --reload, uvicorn
    crea su loop ANTES de importar main.py, así que la policy Proactor que
    seteamos allí llega tarde y no afecta al loop ya construido).
    """
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=_SUBPROCESS_ENV,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )


async def _scan_subproceso() -> list[dict]:
    local_main = _resolver_main_path()
    python_exe = settings.resolver_python_local()

    cmd = [python_exe, str(local_main), "--listar-camaras"]
    logger.info("Escaneando cámaras vía %s", " ".join(cmd[:2]))

    try:
        completed = await asyncio.to_thread(
            _scan_blocking,
            cmd,
            str(local_main.parent),
            settings.camaras_listado_timeout_s,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "La búsqueda de cámaras tardó demasiado. Verifica que las cámaras "
            "estén conectadas e intenta nuevamente.",
        )
    except FileNotFoundError as exc:
        logger.exception("Script local no encontrado: %s", exc)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "No fue posible iniciar la búsqueda de cámaras. "
            "Contacta al administrador del sistema.",
        )
    except Exception:
        logger.exception("Falla inesperada al lanzar subprocess de listado")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "No fue posible buscar las cámaras conectadas. "
            "Contacta al administrador del sistema.",
        )

    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")

    if completed.returncode != 0:
        # Log COMPLETO del stderr para depurar — el caso típico es ImportError
        # de cv2/mediapipe cuando el python_exe NO es el de local/.venv.
        logger.error(
            "Subproceso de listado falló (code=%s).\n  python=%s\n  cwd=%s\n  stderr completo:\n%s",
            completed.returncode, python_exe, str(local_main.parent), stderr,
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "No fue posible obtener la lista de cámaras conectadas. "
            "Verifica que las cámaras estén enchufadas y reintenta.",
        )

    idx = stdout.rfind(CAMARAS_RESULT_MARKER)
    if idx < 0:
        logger.error("Marcador no encontrado. stderr=%s. stdout-tail=%s",
                     stderr[-1000:], stdout[-500:])
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "El sistema no logró leer la lista de cámaras. Reintenta en unos segundos.",
        )

    json_str = stdout[idx + len(CAMARAS_RESULT_MARKER):].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.exception("JSON malformado en listado de cámaras")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "La lista de cámaras devuelta por el sistema no se pudo interpretar.",
        )
