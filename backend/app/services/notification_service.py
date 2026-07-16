from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..config import Settings
from ..core.exceptions import ApplicationError
from ..database.repositories import NotificationRepository
from ..notifications import (
    NotificationProvider,
    TelegramNotificationProvider,
    WhatsAppNotificationProvider,
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._repo = NotificationRepository(db)
        self._provider = self._resolve_provider(settings)

    @staticmethod
    def _resolve_provider(settings: Settings) -> NotificationProvider | None:
        if settings.notification_provider == "telegram":
            return TelegramNotificationProvider(settings)
        if settings.notification_provider == "whatsapp":
            return WhatsAppNotificationProvider(settings)
        return None

    def send(self, message: str, *, recipient: str | None = None) -> dict:
        if self._provider is None:
            raise ApplicationError(
                "No notification provider configured (set NOTIFICATION_PROVIDER)",
                code="notification_provider_disabled",
            )

        result = self._provider.send(message, recipient=recipient)
        log = self._repo.create(
            provider=result.provider,
            message=message,
            recipient=recipient,
            status="sent" if result.success else "failed",
            error_detail=result.error,
        )
        self._db.commit()
        if not result.success:
            logger.warning("Notification failed via %s: %s", result.provider, result.error)
            raise ApplicationError(
                "Failed to send notification",
                code="notification_send_failed",
                details=result.error,
            )
        return {
            "id": log.id,
            "provider": log.provider,
            "status": log.status,
            "message": log.message,
        }

    def list_recent(self, limit: int = 50) -> list:
        return self._repo.list_recent(limit)
