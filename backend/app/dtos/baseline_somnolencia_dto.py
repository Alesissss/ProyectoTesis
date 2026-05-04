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
    camara_id: int = Field(default=1, ge=0, le=10)


class CalibracionResultadoResponse(BaseModel):
    """Estructura devuelta tras una calibración exitosa.

    Incluye el baseline persistido y las métricas crudas reportadas por el
    proceso `local/main.py --calibracion-m1`, así para que la UI las pueda
    mostrar al médico inmediatamente sin re-fetchear.
    """
    baseline: BaselineSomnolenciaResponse
    duracion_real_s: float
    frames_procesados: int
    ventanas_inferidas: int
    fps_observado: Optional[float] = None
