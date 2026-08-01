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
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("%s startup", settings.app_name)
        
        # 0. Initialize Database automatically
        from .database.session import engine
        from .database.base import Base
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

        # Legacy demo cleanup
        from .database.session import SessionLocal
        from .models import (
            Employee, Attendance, Payroll, EmployeeSalary,
            AiDailyInsight, AiMonthlyInsight, ExecutiveSummary,
            NotificationLog, SmartAlert, AiRecommendation
        )

        db = SessionLocal()
        try:
            all_emps = db.query(Employee).all()
            if all_emps:
                legacy_codes = {'E01', 'K6K016', 'EMP-ARJUN', 'John', 'EMP-JOHN', 'E999'}
                legacy_names = {'Arjun', 'John', 'Test Emp', 'John Doe', 'Azeem'}
                is_only_legacy = all(e.employee_code in legacy_codes or e.name in legacy_names for e in all_emps)
                
                if is_only_legacy:
                    logger.info("Detected legacy demo data. Purging database to ensure clean slate.")
                    db.query(Attendance).delete()
                    db.query(Payroll).delete()
                    db.query(EmployeeSalary).delete()
                    db.query(AiDailyInsight).delete()
                    db.query(AiMonthlyInsight).delete()
                    db.query(ExecutiveSummary).delete()
                    db.query(NotificationLog).delete()
                    db.query(SmartAlert).delete()
                    db.query(AiRecommendation).delete()
                    db.query(Employee).delete()
                    db.commit()
                    logger.info("Legacy demo data purged successfully.")
        except Exception as e:
            logger.error(f"Error during legacy demo cleanup: {e}")
            db.rollback()
        finally:
            db.close()
        # 1. Startup Notification
        from .database.session import SessionLocal
        from .services.notification_service import NotificationService
        from .api.settings import get_or_create_settings
        
        db = SessionLocal()
        try:
            get_or_create_settings(db) # Bootstrap if missing
            notification_svc = NotificationService(db, settings)
            notification_svc.send("✅ AI Attendance Agent started successfully.")
        except Exception as e:
            logger.info(f"Startup notification skipped or failed: {e}")
        finally:
            db.close()

        # 2. Start Scheduler
        from .notifications.schedular import NotificationScheduler
        scheduler = NotificationScheduler(settings)
        scheduler.start()
        
        app.state.whisper_model = None
            
        yield
        scheduler.shutdown()
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

    @configured_app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        import os
        import sys
        
        executable = sys.executable
        pid = os.getpid()
        
        # Determine database path
        db_path = settings.sqlalchemy_database_uri
        if db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
            
        return {
            "status": "ok", 
            "environment": settings.environment,
            "pid": str(pid),
            "executable": executable,
            "database": db_path,
            "port": os.environ.get("__TAURI_BACKEND_PORT__", "unknown")
        }

    from fastapi.responses import StreamingResponse
    from fastapi import Request
    import asyncio
    import os

    active_connections = 0

    @configured_app.get("/api/v1/system/events", tags=["system"])
    async def system_events(request: Request):
        nonlocal active_connections
        active_connections += 1
        
        async def event_generator():
            nonlocal active_connections
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    yield "data: ping\n\n"
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                pass
            finally:
                active_connections -= 1
                if active_connections <= 0:
                    async def delayed_shutdown():
                        await asyncio.sleep(3)
                        if active_connections <= 0:
                            logger.info("All browser windows closed. Shutting down backend.")
                            import signal
                            os.kill(os.getpid(), signal.SIGTERM)
                    asyncio.create_task(delayed_shutdown())

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Serve React Frontend in Production
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    @configured_app.get("/{full_path:path}", tags=["frontend"], include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Allow /api routes to fall through to normal 404 behavior instead of returning HTML
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        import sys
        if getattr(sys, 'frozen', False):
            # In PyInstaller, the frontend is bundled in the MEIPASS directory under 'frontend/dist'
            dist_path = Path(sys._MEIPASS) / "frontend" / "dist"
        else:
            dist_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
        
        # If the requested file exists (like JS/CSS assets, favicon), serve it
        file_path = dist_path / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
            
        # Fallback to index.html for React Router SPA behavior
        index_path = dist_path / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
            
        # Fallback for development if the build doesn't exist
        if full_path == "":
            return {"message": f"{settings.app_name} is running (Frontend not built)"}
            
        raise HTTPException(status_code=404, detail="Not Found")

    return configured_app


app = create_app()
