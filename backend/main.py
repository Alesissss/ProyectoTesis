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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"status": False, "message": errores, "data": None},
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
