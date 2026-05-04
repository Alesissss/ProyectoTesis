from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


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
    # Intérprete Python a usar para el subproceso. Por defecto, el del propio
    # backend; en producción suele convenir apuntar al venv de `local/.venv`.
    local_python: str = ""   # vacío = sys.executable
    # Timeout duro en segundos para una calibración (captura + procesamiento).
    calibracion_timeout_s: int = 90


settings = Settings()
