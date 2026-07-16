from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..ai.insights_service import HRInsightsService
from ..config import Settings
from ..database.session import get_db
from ..payroll.payroll_generator import PayrollGenerator
from ..schemas import PayrollGenerateRequest, PayrollRead
from .deps import get_app_settings, get_hr_insights_service, get_payroll_generator

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.post("/generate", response_model=list[PayrollRead])
def generate_payroll(
    body: PayrollGenerateRequest,
    generator: PayrollGenerator = Depends(get_payroll_generator),
    insights: HRInsightsService = Depends(get_hr_insights_service),
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
) -> list[PayrollRead]:
    records = generator.generate_month(body.year, body.month)
    insights.analyze_and_store_monthly(body.year, body.month)
    db.commit()
    if settings.ai_auto_notify:
        insights.send_monthly_payroll_notification(body.year, body.month)
    return [PayrollRead.model_validate(r) for r in records]


@router.get("/{year}/{month}", response_model=list[PayrollRead])
def get_payroll(
    year: int,
    month: int,
    generator: PayrollGenerator = Depends(get_payroll_generator),
) -> list[PayrollRead]:
    records = generator.list_month(year, month)
    return [PayrollRead.model_validate(r) for r in records]
