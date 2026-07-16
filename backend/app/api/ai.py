from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from ..ai.insights_service import HRInsightsService
from ..schemas import (
    AiDailyInsightRead,
    AiMonthlyInsightRead,
    AiRecommendationRead,
    ExecutiveSummaryRead,
    SmartAlertRead,
)
from .deps import get_hr_insights_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/insights/daily", response_model=AiDailyInsightRead)
def daily_insights(
    work_date: date = Query(...),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> AiDailyInsightRead:
    insight = service.get_daily_insight(work_date)
    if insight is None:
        raise HTTPException(status_code=404, detail="No attendance data for this date")
    recommendations = service.get_recommendations(work_date)
    return AiDailyInsightRead.model_validate(insight).model_copy(
        update={
            "recommendations": [AiRecommendationRead.model_validate(r) for r in recommendations],
        }
    )


@router.get("/insights/monthly", response_model=AiMonthlyInsightRead)
def monthly_insights(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> AiMonthlyInsightRead:
    insight = service.get_monthly_insight(year, month)
    if insight is None:
        raise HTTPException(status_code=404, detail="No monthly insight available")
    return AiMonthlyInsightRead.model_validate(insight)


@router.get("/executive-summary", response_model=ExecutiveSummaryRead)
def executive_summary(
    work_date: date = Query(...),
    service: HRInsightsService = Depends(get_hr_insights_service),
) -> ExecutiveSummaryRead:
    summary = service.get_executive_summary(work_date)
    if summary is None:
        raise HTTPException(status_code=404, detail="No executive summary available")
    recommendations = service.get_recommendations(work_date)
    alerts = service.get_alerts(work_date=work_date)
    return ExecutiveSummaryRead.model_validate(summary).model_copy(
        update={
            "recommendations": [AiRecommendationRead.model_validate(r) for r in recommendations],
            "alerts": [SmartAlertRead.model_validate(a) for a in alerts],
        }
    )
