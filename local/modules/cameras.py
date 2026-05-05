"""
Perfiles de cámara para el Módulo 1 (visión + rPPG) — VigilanceAI.

Centraliza los parámetros de captura por dispositivo para que `m1_vision.py` y
`main.py` no tengan que hardcodear índice/backend/FOURCC. Cuando se cambia de
cámara basta con seleccionar otro perfil — el código del pipeline no toca.

Selección, en orden de precedencia:
    1. Argumento `--camera-profile` en CLI (main.py / m1_vision.py demo).
    2. Variable de entorno `VIGILANCE_CAMERA_PROFILE`.
    3. `DEFAULT_PROFILE` (= "alpcam", la cámara de producción).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import cv2


@dataclass(frozen=True)
class CameraConfig:
    name: str            # descripción humana — para logs
    index: int           # índice de OpenCV
    backend: int         # cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY...
    width: int
    height: int
    fps_request: int     # fps a solicitar al driver
    fps_real: float      # fps medido empíricamente — usado para HRV/Butterworth
    fourcc: str | None   # "MJPG", "YUY2"... None si el driver no respeta FOURCC


# ─── Perfiles ────────────────────────────────────────────────────────────────
#
# webcam: la VGA WebCam integrada de la laptop. Se cae a 640x480, ~30 fps.
#         Útil solo como fallback de emergencia — no recomendada ni para M1.
#
# gopro:  GoPro Hero 11 Black expuesta vía "GoPro Webcam Desktop Utility"
#         con el modo "Show Preview" activo. ROLLING SHUTTER → solo para
#         pruebas funcionales del pipeline, NO para el informe final.
#         Validada el 2026-05-05 con diagnostico_camara.py: 70.46 fps reales
#         a 1280x720 con backend DSHOW. La cámara virtual de GoPro no expone
#         un FOURCC UVC estándar; por eso fourcc=None.
#
# alpcam: cámara de producción — módulo USB UVC con sensor onsemi AR0234CS,
#         obturador global. Validada el 2026-05-03 con la unidad B0DM92T2MC:
#         57.6 fps reales a 1280x720 con MSMF + MJPG por USB 2.0.
#         La unidad nueva en compra (B0CXDS8F6Q) usa el MISMO sensor — al
#         llegar, re-correr `diagnostico_camara.py` y actualizar fps_real
#         si difiere.

PROFILES: dict[str, CameraConfig] = {
    "webcam": CameraConfig(
        name="Webcam integrada (laptop, VGA)",
        index=0,
        backend=cv2.CAP_DSHOW,
        width=640,
        height=480,
        fps_request=30,
        fps_real=29.65,
        fourcc=None,
    ),
    "gopro": CameraConfig(
        name="GoPro Hero 11 Black (GoPro Webcam Utility)",
        index=2,
        backend=cv2.CAP_DSHOW,
        width=1280,
        height=720,
        fps_request=30,
        fps_real=70.46,
        fourcc=None,
    ),
    "alpcam": CameraConfig(
        name="ALPCAM AR0234 USB (sensor onsemi global shutter)",
        index=1,
        backend=cv2.CAP_MSMF,
        width=1280,
        height=720,
        fps_request=60,
        fps_real=57.6,
        fourcc="MJPG",
    ),
}

DEFAULT_PROFILE = "alpcam"
ENV_VAR = "VIGILANCE_CAMERA_PROFILE"


def get_profile(name: str | None = None) -> CameraConfig:
    """Resuelve el perfil de cámara aplicando la precedencia documentada."""
    chosen = name or os.getenv(ENV_VAR) or DEFAULT_PROFILE
    if chosen not in PROFILES:
        opciones = ", ".join(PROFILES.keys())
        raise ValueError(
            f"Perfil de cámara desconocido: {chosen!r}. Opciones válidas: {opciones}."
        )
    return PROFILES[chosen]


def listar_perfiles() -> list[str]:
    return list(PROFILES.keys())
