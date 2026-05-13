import asyncio
import logging
import sys

# ── Event loop policy en Windows ─────────────────────────────────────────────
# `asyncio.create_subprocess_exec` (usado por dispositivos_service /
# evaluacion_service / calibracion_service) requiere ProactorEventLoop. Si
# uvicorn arranca con SelectorEventLoop (puede pasar según versión / flags),
# todo subprocess crashea con `NotImplementedError`. Forzamos la policy
# correcta ANTES de importar cualquier otra cosa.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import (
    auth_router,
    usuario_router,
    evaluacion_router,
    baseline_router,
    baseline_somnolencia_router,
    calibracion_router,
    dispositivos_router,
    rol_router,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": False, "message": exc.detail, "data": None},
    )


_PYDANTIC_MSG_ES = {
    "missing": "es obligatorio",
    "string_too_short": "es muy corto",
    "string_too_long": "es muy largo",
    "value_error.email": "no es un correo válido",
    "value_error": "no tiene un valor válido",
    "type_error": "tiene un tipo de dato incorrecto",
    "greater_than": "debe ser mayor al mínimo permitido",
    "less_than": "debe ser menor al máximo permitido",
    "greater_than_equal": "es menor al mínimo permitido",
    "less_than_equal": "supera el máximo permitido",
    "string_pattern_mismatch": "tiene un formato no válido",
    "json_invalid": "no es un JSON válido",
}

_CAMPO_ES = {
    "email": "El correo",
    "password": "La contraseña",
    "nombre": "El nombre",
    "apellido": "El apellido",
    "id_rol": "El rol",
    "p_somnolencia": "La probabilidad de somnolencia",
    "p_fatiga_fisiologica": "La probabilidad de fatiga",
    "p_total": "La probabilidad total",
    "dictamen": "El dictamen",
    "duracion_s": "La duración",
    "duracion_captura_s": "La duración de captura",
    "camera_profile": "El perfil de cámara",
    "camara_id": "El identificador de cámara",
    "puerto_arduino": "El puerto del Arduino",
}


def _humanizar_validacion(errores: list[dict]) -> str:
    """Convierte errores Pydantic (en inglés con paths técnicos) a mensajes
    cortos en español que un usuario final pueda entender."""
    mensajes: list[str] = []
    for err in errores:
        loc = [str(l) for l in err.get("loc", []) if l not in ("body", "query", "path")]
        campo_raw = loc[-1] if loc else "el dato"
        campo = _CAMPO_ES.get(campo_raw, f"El campo '{campo_raw}'")
        tipo = err.get("type", "")
        # Prioriza match exacto; fallback a familia (split por ".")
        problema = _PYDANTIC_MSG_ES.get(tipo) or _PYDANTIC_MSG_ES.get(tipo.split(".")[0]) \
                   or "tiene un valor inválido"
        mensajes.append(f"{campo} {problema}")
    return ". ".join(mensajes) + "."


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    mensaje = _humanizar_validacion(exc.errors())
    logger.warning("Validación fallida en %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"status": False, "message": mensaje, "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Excepción no manejada en %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"status": False, "message": "Error interno del servidor", "data": None},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router,       prefix="/auth",        tags=["Autenticación"])
app.include_router(usuario_router.router,    prefix="/usuarios",    tags=["Usuarios"])
app.include_router(evaluacion_router.router, prefix="/evaluaciones",tags=["Evaluaciones"])
app.include_router(baseline_router.router,   prefix="/baselines",   tags=["Baselines EMG"])
app.include_router(baseline_somnolencia_router.router,
                   prefix="/baselines/somnolencia", tags=["Baselines Somnolencia (M1)"])
app.include_router(calibracion_router.router,
                   prefix="/calibracion",           tags=["Calibración"])
app.include_router(rol_router.router,        prefix="/roles",        tags=["Roles"])
app.include_router(dispositivos_router.router,
                   prefix="/dispositivos",         tags=["Dispositivos"])


@app.get("/", tags=["Health"])
async def health():
    return {"status": True, "message": "OK", "data": {"app": settings.app_name, "version": settings.app_version}}
