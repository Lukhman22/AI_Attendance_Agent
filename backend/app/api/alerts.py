from datetime import date

from fastapi import APIRouter, Depends, Query

from ..ai.insights_service import HRInsightsService
from ..schemas import SmartAlertRead
from .deps import get_hr_insights_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[SmartAlertRead])
def list_alerts(
    work_date: date | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> list[SmartAlertRead]:
    alerts = service.get_alerts(work_date=work_date, year=year, month=month)
    return [SmartAlertRead.model_validate(a) for a in alerts]
