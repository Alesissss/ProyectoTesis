"""DTOs para inspección de hardware (cámaras detectadas)."""
from typing import Optional

from pydantic import BaseModel, Field


class CamaraDisponibleResponse(BaseModel):
    """Una cámara detectada por `local/main.py --listar-camaras`.

    El backend solo retransmite — el subprocess es la fuente de verdad de
    qué dispositivos hay disponibles y cómo están configurados.
    """
    index: int = Field(..., description="Índice OpenCV de la cámara")
    backend: str = Field(..., description="Backend usado: DSHOW | MSMF")
    width: int
    height: int
    profile: Optional[str] = Field(
        default=None,
        description="ID del perfil en cameras.py ('alpcam' | 'gopro' | 'webcam') o null si la cámara no matchea ningún perfil conocido.",
    )
    label: str = Field(..., description="Texto para mostrar al usuario en el dropdown")
