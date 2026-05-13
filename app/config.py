"""
INMERSIVA — Configuración central de la aplicación
Todas las variables sensibles se cargan desde el archivo .env
Nunca hardcodees contraseñas o API keys directamente en el código.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic.
    Pydantic valida automáticamente que las variables existan y sean del tipo correcto.
    """

    # ─── Proyecto ─────────────────────────────────────────────────────────────
    PROJECT_NAME: str = "INMERSIVA"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ─── Base de datos ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/inmersiva"

    # ─── Seguridad / JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = "cambia-esto-por-una-clave-segura-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas por sesión

    # ─── OpenAI ───────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ─── Upload Post (publicación en redes sociales) ──────────────────────────
    UPLOADPOST_API_KEY: str = ""
    UPLOADPOST_USER: str = ""

    # ─── Archivos y almacenamiento ────────────────────────────────────────────
    UPLOAD_DIR: str = "app/uploads"
    GENERATED_DIR: str = "app/generated"
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # ─── Dominio ──────────────────────────────────────────────────────────────
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna la instancia de configuración (cacheada para no releer el .env en cada request).
    Úsala así en cualquier parte del proyecto:
        from app.config import settings
    """
    return Settings()


# Instancia global lista para importar
settings = get_settings()
