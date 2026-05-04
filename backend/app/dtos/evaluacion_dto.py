"""
DTOs de evaluaciones.
El script local (edge) envía EvaluacionRequest al endpoint POST /evaluaciones.
El backend valida, persiste y devuelve EvaluacionResponse.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
import uuid
from datetime import datetime
from enum import Enum


class DictamenEnum(str, Enum):
    APTO = "APTO"
    ATENCION = "ATENCION"
    NO_APTO = "NO_APTO"


class EvaluacionRequest(BaseModel):
    """
    Payload enviado por el script local tras procesar video + EMG.
    El backend NO valida la coherencia de los valores (confía en el edge).
    """
    # El script envía su propio user_id (extraído del JWT que usó para autenticarse)
    p_somnolencia: float = Field(..., ge=0.0, le=1.0)
    p_fatiga_fisiologica: float = Field(..., ge=0.0, le=1.0)
    p_total: float = Field(..., ge=0.0, le=1.0)
    dictamen: DictamenEnum
    umbral_usado: float = Field(default=0.50, ge=0.0, le=1.0)

    # Features crudas — schema libre
    features_conductuales: Optional[Dict[str, Any]] = None
    features_emg: Optional[Dict[str, Any]] = None
    features_hrv: Optional[Dict[str, Any]] = None
    metadatos: Optional[Dict[str, Any]] = None
    duracion_captura_s: int = Field(default=30, ge=1)

    # ID del baseline activo usado para esta evaluación (lo envía el script local)
    id_baseline_usado: Optional[uuid.UUID] = None


class EvaluacionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_evaluacion: uuid.UUID
    id_usuario: uuid.UUID
    p_somnolencia: float
    p_fatiga_fisiologica: float
    p_total: float
    dictamen: str
    umbral_usado: float
    features_conductuales: Optional[Dict[str, Any]]
    features_emg: Optional[Dict[str, Any]]
    features_hrv: Optional[Dict[str, Any]]
    duracion_captura_s: int
    fecha_registro: datetime


class EvaluacionResumenResponse(BaseModel):
    """Vista resumida para listados."""
    model_config = {"from_attributes": True}

    id_evaluacion: uuid.UUID
    dictamen: str
    p_total: float
    fecha_registro: datetime
