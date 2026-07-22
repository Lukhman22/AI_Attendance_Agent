from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..schemas import NotificationLogRead, NotificationSendRequest
from ..schemas.notification_settings import NotificationSettingsUpdate, NotificationSettingsResponse
from ..services.notification_service import (
    NotificationService, 
    send_daily_summary, 
    send_monthly_payroll_summary
)
from ..models import NotificationSettings
from .deps import get_notification_service, get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send")
def send_notification(
    body: NotificationSendRequest,
    service: NotificationService = Depends(get_notification_service),
):
    return service.send(body.message)


@router.get("/logs", response_model=list[NotificationLogRead])
def notification_logs(
    limit: int = Query(50, ge=1, le=200),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationLogRead]:
    return [NotificationLogRead.model_validate(item) for item in service.list_recent(limit)]


# --- NEW NOTIFICATION CENTER ENDPOINTS ---

@router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(db: Session = Depends(get_db)):
    settings = db.query(NotificationSettings).first()
    if not settings:
        # Create default settings row if it doesn't exist yet
        settings = NotificationSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put("/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    settings_in: NotificationSettingsUpdate,
    db: Session = Depends(get_db)
):
    settings = db.query(NotificationSettings).first()
    if not settings:
        settings = NotificationSettings(id=1)
        db.add(settings)
    
    # Update only the provided fields
    for field, value in settings_in.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
        
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/trigger/daily-summary")
def trigger_daily_summary(date: str | None = None, db: Session = Depends(get_db)):
    # If no date is passed, the service will default to today
    try:
        result = send_daily_summary(db, target_date=date)
        return {"status": "success", "message": "Daily summary sent successfully", "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/monthly-summary")
def trigger_monthly_summary(month: int, year: int, db: Session = Depends(get_db)):
    try:
        result = send_monthly_payroll_summary(db, month=month, year=year)
        return {"status": "success", "message": "Monthly summary sent successfully", "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))