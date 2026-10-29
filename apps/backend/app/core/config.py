from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno (ver infra/local/.env.local)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://udela:udela_local_pass@postgres:5432/udelaconecta"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días
    STORAGE_DIR: str = "/app/storage"
    PUBLIC_STORAGE_BASE_URL: str = "http://localhost:3000/storage"
    MAX_IMAGE_BYTES: int = 5 * 1024 * 1024
    # Tras LOGIN_MAX_INTENTOS fallidos seguidos, la cuenta queda bloqueada LOGIN_BLOQUEO_MINUTOS
    LOGIN_MAX_INTENTOS: int = 5
    LOGIN_BLOQUEO_MINUTOS: int = 15
    # Orígenes permitidos para CORS, separados por coma
    CORS_ORIGINS: str = "http://localhost:4200"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _secreto_seguro(cls, valor: str) -> str:
        # Evita levantar producción con el valor de ejemplo de .env.vps.example
        if len(valor) < 32 or "CAMBIAR" in valor.upper():
            raise ValueError("JWT_SECRET_KEY debe ser aleatoria y tener al menos 32 caracteres")
        return valor

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
