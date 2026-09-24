"""Application settings loaded from environment (PRD §8.3, §13)."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET_VALUES = {"", "changeme", "dev-secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"  # "production" enables strict secret checks
    database_url: str = "postgresql+psycopg://fallguard:fallguard@localhost:5432/fallguard"
    jwt_secret: str = ""
    csrf_secret: str = ""
    cors_origins: str = "http://localhost:3000"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@fallguard.local"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @model_validator(mode="after")
    def _refuse_default_secrets_in_production(self) -> "Settings":
        if self.is_production:
            for name in ("jwt_secret", "csrf_secret"):
                if getattr(self, name) in _DEFAULT_SECRET_VALUES:
                    raise ValueError(
                        f"{name} must be set to a non-default value when env=production"
                    )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
