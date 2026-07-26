from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..models import NotificationSettings
from ..schemas.notification_settings import NotificationSettingsResponse, NotificationSettingsUpdate

from ..notifications.telegram import TelegramNotificationProvider
from ..config.settings import settings
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

class TelegramTestRequest(BaseModel):
    telegram_bot_token: str
    telegram_chat_id: str

def get_or_create_settings(db: Session) -> NotificationSettings:
    db_settings = db.query(NotificationSettings).first()
    if not db_settings:
        from ..config import get_settings
        app_settings = get_settings()
        db_settings = NotificationSettings(
            telegram_bot_token=app_settings.telegram_token,
            telegram_chat_id=app_settings.telegram_chat_id,
            telegram_enabled=bool(app_settings.telegram_token and app_settings.telegram_chat_id)
        )
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
    return db_settings

@router.get("", response_model=NotificationSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    # current_user = Depends(require_admin)  # Handled by global RBAC dependency in main
):
    db_settings = get_or_create_settings(db)
    return db_settings

@router.put("", response_model=NotificationSettingsResponse)
def update_settings(
    update_data: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
):
    db_settings = get_or_create_settings(db)
    
    if update_data.telegram_enabled:
        if not update_data.telegram_bot_token or not update_data.telegram_chat_id:
            raise HTTPException(
                status_code=400, 
                detail="Telegram Bot Token and Chat ID are required when Telegram is enabled."
            )
            
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(db_settings, key, value)
        
    db.commit()
    db.refresh(db_settings)
    return db_settings

@router.post("/test-telegram")
def test_telegram(
    test_data: TelegramTestRequest,
    db: Session = Depends(get_db),
):
    if not test_data.telegram_bot_token or not test_data.telegram_chat_id:
        raise HTTPException(
            status_code=400, 
            detail="Both Telegram Bot Token and Chat ID are required."
        )

    provider = TelegramNotificationProvider(
        token=test_data.telegram_bot_token,
        chat_id=test_data.telegram_chat_id
    )
    
    result = provider.send("✅ AI Attendance Agent Telegram configuration successful.")
    
    if not result.success:
        raise HTTPException(
            status_code=400, 
            detail=f"Telegram test failed: {result.error}"
        )
        
    return {"status": "success", "message": "Test notification sent successfully"}
