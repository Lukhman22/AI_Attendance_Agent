from fastapi import APIRouter

from .alerts import router as alerts_router
from .attendance import router as attendance_router
from .ai import router as ai_router
from .employees import router as employees_router
from .notifications import router as notifications_router
from .payroll import router as payroll_router
from .reports import router as reports_router
from .annotations import router as annotations_router
from .settings import router as settings_router

api_router = APIRouter()
api_router.include_router(settings_router)
api_router.include_router(attendance_router)
api_router.include_router(payroll_router)
api_router.include_router(employees_router)
api_router.include_router(notifications_router)
api_router.include_router(reports_router)
api_router.include_router(ai_router)
api_router.include_router(alerts_router)
api_router.include_router(annotations_router)
