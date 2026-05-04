# Importar todos los modelos para que Alembic los detecte en la metadata
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.rol_permiso import RolPermiso
from app.models.usuario import Usuario
from app.models.baseline_emg import BaselineEmg
from app.models.evaluacion import Evaluacion
from app.models.auditoria_log import AuditoriaLog

__all__ = [
    "Rol", "Permiso", "RolPermiso",
    "Usuario", "BaselineEmg", "Evaluacion",
    "AuditoriaLog",
]
