from sqlalchemy import Column, Integer, Boolean, String
from ...database.base import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    telegram_enabled = Column(Boolean, default=False)
    telegram_bot_token = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)