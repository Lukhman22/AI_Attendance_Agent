from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationSettingsBase(BaseModel):
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class NotificationSettingsUpdate(NotificationSettingsBase):
    pass


class NotificationSettingsResponse(NotificationSettingsBase):
    id: int

    # Configures Pydantic to read data directly from the SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)