"""DTOs de baselines EMG."""

from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class BaselineCreateRequest(BaseModel):
    """El script local envía los valores del baseline tras la fase de calibración."""
    rms_emg: float = Field(..., gt=0)
    freq_mediana: float = Field(..., gt=0)
    freq_media: float = Field(..., gt=0)
    sdnn: Optional[float] = Field(default=None, gt=0)
    rmssd: Optional[float] = Field(default=None, gt=0)
    pnn50: Optional[float] = Field(default=None, ge=0, le=100)


class BaselineResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_baseline: uuid.UUID
    id_usuario: uuid.UUID
    rms_emg: float
    freq_mediana: float
    freq_media: float
    sdnn: Optional[float]
    rmssd: Optional[float]
    pnn50: Optional[float]
    activo: bool
    fecha_registro: datetime
