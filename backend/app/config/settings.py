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


def _env_float(key: str, default: float) -> float:
    value = _env(key)
    if value is None:
        return default
    return float(value)


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
    environment: Literal["local", "development", "staging", "production", "test"] = Field(
        default_factory=_env_environment
    )
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

    # HR rules (env defaults; DB SalaryRule can override per deployment)
    min_working_hours: float = Field(default_factory=lambda: _env_float("MIN_WORKING_HOURS", 8.0))
    max_payable_hours: float = Field(default_factory=lambda: _env_float("MAX_PAYABLE_HOURS", 8.0))
    overtime_paid: bool = Field(default_factory=lambda: _env_bool("OVERTIME_PAID", False))
    break_duration_required: bool = Field(default_factory=lambda: _env_bool("BREAK_DURATION_REQUIRED", True))
    default_working_days_per_month: int = Field(
        default_factory=lambda: _env_int("DEFAULT_WORKING_DAYS_PER_MONTH", 26)
    )
    # Shared monthly salary for payroll (internship / flat-rate mode)
    default_monthly_salary: float = Field(
        default_factory=lambda: _env_float("DEFAULT_MONTHLY_SALARY", 30000.0)
    )

    # Attendance source abstraction: file (csv/excel) or future api
    attendance_provider: Literal["file", "api"] = Field(
        default_factory=lambda: _env("ATTENDANCE_PROVIDER", "file").lower()  # type: ignore[arg-type]
    )
    @property
    def app_data_dir(self) -> Path:
        import platform
        import os
        system = platform.system()
        if system == "Windows":
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
            return base / "AIAttendanceAgent"
        elif system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "AIAttendanceAgent"
        else:
            return Path.home() / ".ai_attendance_agent"

    @property
    def uploads_dir(self) -> str:
        d = _env("UPLOADS_DIR", str(self.app_data_dir / "uploads"))
        Path(d).mkdir(parents=True, exist_ok=True)
        return d

    @property
    def reports_dir(self) -> str:
        d = _env("REPORTS_DIR", str(self.app_data_dir / "reports"))
        Path(d).mkdir(parents=True, exist_ok=True)
        return d

    # Notifications
    notification_provider: Literal["telegram", "none"] = Field(
        default_factory=lambda: _env("NOTIFICATION_PROVIDER", "telegram").lower()  # type: ignore[arg-type]
    )
    telegram_token: str | None = Field(default_factory=lambda: _env("TELEGRAM_TOKEN"))
    telegram_chat_id: str | None = Field(default_factory=lambda: _env("TELEGRAM_CHAT_ID"))
    report_time: str = Field(default_factory=lambda: _env("REPORT_TIME", "18:30"))

    # Upload safety
    max_upload_bytes: int = Field(default_factory=lambda: _env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
    allowed_upload_extensions: list[str] = Field(
        default_factory=lambda: _env_csv(
            "ALLOWED_UPLOAD_EXTENSIONS",
            [".csv", ".xlsx", ".xlsm", ".xls", ".pdf"],
        )
    )

    # Optional local employee directory (salary / master data for attendance identity enrichment).
    # Set EMPLOYEE_DIRECTORY_FILE env var to a CSV path to enable this feature.
    # Defaults to None — no pre-loaded directory on fresh installs.
    employee_directory_file: str | None = Field(
        default_factory=lambda: _env("EMPLOYEE_DIRECTORY_FILE", None)
    )
    auto_register_employees_from_attendance: bool = Field(
        default_factory=lambda: _env_bool("AUTO_REGISTER_EMPLOYEES_FROM_ATTENDANCE", True)
    )

    # AI
    openai_api_key: str | None = Field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = Field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o-mini"))

    # AI analysis thresholds
    late_arrival_time: str = Field(default_factory=lambda: _env("LATE_ARRIVAL_TIME", "09:30"))
    short_workday_threshold_hours: float = Field(
        default_factory=lambda: _env_float("SHORT_WORKDAY_THRESHOLD_HOURS", 8.0)
    )
    extremely_short_workday_hours: float = Field(
        default_factory=lambda: _env_float("EXTREMELY_SHORT_WORKDAY_HOURS", 2.0)
    )
    ai_auto_notify: bool = Field(default_factory=lambda: _env_bool("AI_AUTO_NOTIFY", True))

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url

        # Desktop standalone default: SQLite in correct per-user app data directory
        app_dir = self.app_data_dir
        app_dir.mkdir(parents=True, exist_ok=True)
        db_path = app_dir / "database.sqlite3"
        return f"sqlite:///{db_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()