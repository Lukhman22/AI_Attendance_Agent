from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import NotificationLog


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        provider: str,
        message: str,
        recipient: str | None = None,
        status: str = "pending",
        error_detail: str | None = None,
    ) -> NotificationLog:
        log = NotificationLog(
            provider=provider,
            recipient=recipient,
            message=message,
            status=status,
            error_detail=error_detail,
        )
        self._db.add(log)
        self._db.flush()
        return log

    def list_recent(self, limit: int = 50) -> list[NotificationLog]:
        stmt = select(NotificationLog).order_by(NotificationLog.id.desc()).limit(limit)
        return list(self._db.scalars(stmt).all())
