import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import api_router
from .config import Settings, get_settings
from .core.exceptions import register_exception_handlers
from .core.logging import setup_logging
from .middleware import RequestIdMiddleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings)

    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("%s startup", settings.app_name)
        yield
        logger.info("%s shutdown", settings.app_name)

    configured_app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )

    configured_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins or ["*"],
        allow_credentials="*" not in (settings.backend_cors_origins or ["*"]),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    configured_app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts or ["*"],
    )
    configured_app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(configured_app)
    configured_app.include_router(api_router, prefix=settings.api_v1_prefix)

    @configured_app.get("/", tags=["system"])
    def home() -> dict[str, str]:
        return {"message": f"{settings.app_name} is running"}

    @configured_app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return configured_app


app = create_app()
