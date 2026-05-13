"""DTOs del baseline personal de somnolencia (M1)."""

from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class BaselineSomnolenciaCreateRequest(BaseModel):
    """Payload enviado por el script local tras una calibración M1.

    p_somnolencia es el promedio del BiLSTM en el estado alerta declarado
    del sujeto. Los demás campos son métricas conductuales auxiliares para
    diagnóstico y trazabilidad de la captura.
    """
    p_somnolencia: float = Field(..., ge=0.0, le=1.0)
    ear_promedio: Optional[float] = Field(default=None, gt=0.0)
    mar_promedio: Optional[float] = Field(default=None, ge=0.0)
    duracion_s: Optional[float] = Field(default=None, gt=0.0)
    frames_procesados: Optional[int] = Field(default=None, ge=0)


class BaselineSomnolenciaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_baseline: uuid.UUID
    id_usuario: uuid.UUID
    p_somnolencia: float
    ear_promedio: Optional[float]
    mar_promedio: Optional[float]
    duracion_s: Optional[float]
    frames_procesados: Optional[int]
    activo: bool
    fecha_registro: datetime


class CalibracionIniciarRequest(BaseModel):
    """Parámetros opcionales para disparar la calibración M1 desde React."""
    duracion_s: int = Field(default=30, ge=10, le=120)
    # Perfil de cámara — id del listado de /dispositivos/camaras
    # ("alpcam" | "gopro" | "webcam" | None). Si viene, fija backend, FOURCC
    # y resolución del subproceso. Es la vía recomendada.
    camera_profile: Optional[str] = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9_-]{1,32}$",
    )
    # Override del índice de cámara (legacy / opcional). Si camera_profile está
    # presente, este índice prevalece sobre el del perfil; útil cuando hay dos
    # cámaras del mismo modelo conectadas.
    camara_id: Optional[int] = Field(default=None, ge=0, le=10)
    # Puerto serie del Arduino sEMG para calibrar M2 (EMG) en paralelo.
    # None → auto-detección; "skip" o cadena vacía manejada por el script.
    puerto_arduino: Optional[str] = Field(default=None)


class BaselineM2Resumen(BaseModel):
    """Resumen del baseline fisiológico M2 emitido en la calibración."""
    id_baseline: Optional[uuid.UUID] = None
    rms_emg: Optional[float] = None
    freq_mediana: Optional[float] = None
    freq_media: Optional[float] = None
    sdnn: Optional[float] = None
    rmssd: Optional[float] = None
    pnn50: Optional[float] = None
    emg_valido: bool = False
    emg_ratio_60hz: Optional[float] = None
    emg_motivo: Optional[str] = None
    arduino_detectado: bool = False
    n_muestras_emg: int = 0


class CalibracionResultadoResponse(BaseModel):
    """Estructura devuelta tras una calibración exitosa.

    Incluye AMBOS baselines (M1 y M2) capturados en el mismo intervalo,
    además de métricas crudas para que la UI los muestre al médico
    inmediatamente sin re-fetchear.
    """
    baseline: BaselineSomnolenciaResponse          # M1 (visión)
    baseline_m2: Optional[BaselineM2Resumen] = None  # M2 (EMG + HRV)
    duracion_real_s: float
    frames_procesados: int
    ventanas_inferidas: int
    fps_observado: Optional[float] = None
