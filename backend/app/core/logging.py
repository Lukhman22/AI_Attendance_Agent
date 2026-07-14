import json
import logging
from logging.config import dictConfig
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.app.config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging(settings: "Settings") -> None:
    formatter = "json" if settings.log_format == "json" else "plain"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "json": {
                    "()": JsonFormatter,
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": settings.log_level,
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": settings.log_level, "propagate": False},
                "uvicorn.error": {"level": settings.log_level},
                "uvicorn.access": {"handlers": ["default"], "level": settings.log_level, "propagate": False},
                "sqlalchemy.engine": {"level": "INFO" if settings.db_echo else "WARNING"},
            },
        }
    )
