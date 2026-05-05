import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


def _detectar_local_python() -> str:
    """Auto-detecta el intérprete Python para el subproceso `local/main.py`.

    Orden de búsqueda:
      1. Variable de entorno LOCAL_PYTHON (si está seteada).
      2. `local/.venv/Scripts/python.exe` (Windows) o `local/.venv/bin/python` (Unix).
      3. `sys.executable` (el del backend) — ÚLTIMO RECURSO. Probablemente no
         tenga cv2/mediapipe/torch instalados → el subprocess fallará con
         ImportError. El log lo dejará claro.

    El sistema embebido y el backend tienen venvs SEPARADOS por diseño
    (RNF-12 + arquitectura del proyecto). Forzar `sys.executable` rompe el
    pipeline porque el venv del backend no instala las dependencias de
    visión por elección arquitectónica.
    """
    backend_dir = Path(__file__).resolve().parents[1]   # backend/
    repo_root   = backend_dir.parent                    # raíz del repo
    candidatos = [
        repo_root / "local" / ".venv" / "Scripts" / "python.exe",  # Windows
        repo_root / "local" / ".venv" / "bin" / "python",          # Linux/Mac
    ]
    for c in candidatos:
        if c.exists():
            return str(c)
    # Fallback: el python del backend. Casi seguro fallará por imports.
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base de datos
    database_url: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # CORS
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # App
    app_name: str = "VigilanceAI API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Sistema embebido (carpeta local/)
    # Path al main.py del subproceso de captura. Resolución por defecto
    # asume layout `<repo>/backend/` y `<repo>/local/main.py`.
    local_main_path: str = "../local/main.py"
    # Intérprete Python a usar para el subproceso. Si no se setea, se intenta
    # auto-detectar `local/.venv/...python` (ver _detectar_local_python).
    local_python: str = ""
    # Timeout duro en segundos para una calibración (captura + procesamiento).
    calibracion_timeout_s: int = 90
    # Timeout duro para una evaluación completa: cubre captura (≤30 s típica),
    # lectura paralela del Arduino, procesamiento M1+M2+M3 y POST al backend.
    # Se deja más holgado que la calibración por la rama EMG y el FFT.
    evaluacion_timeout_s: int = 180
    # Listado de cámaras: el primer scan tarda ~5-10 s (DSHOW + MSMF en
    # índices conocidos). El resultado se cachea por este tiempo en el
    # backend para que recargar la página no re-escanee. Botón "refrescar"
    # del frontend pasa ?refresh=true.
    camaras_cache_ttl_s: int = 300
    camaras_listado_timeout_s: int = 60

    def resolver_python_local(self) -> str:
        """Devuelve el path al intérprete que debe ejecutar `local/main.py`.

        Resuelve en este orden:
          1. self.local_python si fue seteado vía .env / variable de entorno.
          2. Auto-detección en `local/.venv/...python`.
          3. sys.executable (el del backend) como último recurso.
        """
        if self.local_python:
            return self.local_python
        detectado = _detectar_local_python()
        return detectado or sys.executable


settings = Settings()
