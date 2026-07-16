from fastapi import APIRouter, Depends, Query

from ..schemas import NotificationLogRead, NotificationSendRequest
from ..services.notification_service import NotificationService
from .deps import get_notification_service

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
