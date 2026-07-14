from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BACKEND_ROOT / ".env", override=False)


def _env(key: str, default: str | None = None) -> str | None:
    value = getenv(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_bool(key: str, default: bool = False) -> bool:
    value = _env(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    value = _env(key)
    if value is None:
        return default
    return int(value)


def _env_optional_path(key: str, default: str | None) -> str | None:
    value = _env(key, default)
    if value is None:
        return None
    if value.lower() in {"none", "null", "false", "off"}:
        return None
    return value


def _env_csv(key: str, default: list[str] | None = None) -> list[str]:
    value = _env(key)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_environment() -> str:
    value = _env("ENVIRONMENT", _env("APP_ENV", "development")).lower()
    aliases = {
        "dev": "development",
        "prod": "production",
        "stage": "staging",
    }
    return aliases.get(value, value)


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    app_name: str = Field(default_factory=lambda: _env("APP_NAME", "AI Attendance Agent"))
    app_version: str = Field(default_factory=lambda: _env("APP_VERSION", "1.0.0"))
    environment: Literal["local", "development", "staging", "production", "test"] = Field(default_factory=_env_environment)
    debug: bool = Field(default_factory=lambda: _env_bool("DEBUG", False))

    api_v1_prefix: str = Field(default_factory=lambda: _env("API_V1_PREFIX", "/api/v1"))
    docs_url: str | None = Field(default_factory=lambda: _env_optional_path("DOCS_URL", "/docs"))
    redoc_url: str | None = Field(default_factory=lambda: _env_optional_path("REDOC_URL", "/redoc"))
    openapi_url: str | None = Field(default_factory=lambda: _env_optional_path("OPENAPI_URL", "/openapi.json"))

    database_url: str | None = Field(default_factory=lambda: _env("DATABASE_URL"))
    postgres_server: str = Field(default_factory=lambda: _env("POSTGRES_SERVER", "localhost"))
    postgres_port: int = Field(default_factory=lambda: _env_int("POSTGRES_PORT", 5432))
    postgres_user: str = Field(default_factory=lambda: _env("POSTGRES_USER", "postgres"))
    postgres_password: str = Field(default_factory=lambda: _env("POSTGRES_PASSWORD", "postgres"))
    postgres_db: str = Field(default_factory=lambda: _env("POSTGRES_DB", "ai_attendance_agent"))

    db_echo: bool = Field(default_factory=lambda: _env_bool("DB_ECHO", False))
    db_pool_size: int = Field(default_factory=lambda: _env_int("DB_POOL_SIZE", 10))
    db_max_overflow: int = Field(default_factory=lambda: _env_int("DB_MAX_OVERFLOW", 20))
    db_pool_timeout: int = Field(default_factory=lambda: _env_int("DB_POOL_TIMEOUT", 30))
    db_pool_recycle: int = Field(default_factory=lambda: _env_int("DB_POOL_RECYCLE", 1800))

    log_level: str = Field(default_factory=lambda: _env("LOG_LEVEL", "INFO").upper())
    log_format: Literal["plain", "json"] = Field(default_factory=lambda: _env("LOG_FORMAT", "plain").lower())

    backend_cors_origins: list[str] = Field(default_factory=lambda: _env_csv("BACKEND_CORS_ORIGINS"))
    trusted_hosts: list[str] = Field(default_factory=lambda: _env_csv("TRUSTED_HOSTS", ["*"]))

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        database = quote_plus(self.postgres_db)
        return (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{self.postgres_server}:{self.postgres_port}/{database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
