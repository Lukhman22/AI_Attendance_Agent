from __future__ import annotations

import logging

import httpx

from ..config import Settings
from .base import NotificationProvider, NotificationResult

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096


class TelegramNotificationProvider(NotificationProvider):
    name = "telegram"

    def __init__(
    self,
    client: httpx.Client | None = None,
    token: str | None = None,
    chat_id: str | None = None,
) -> None:
        self._token = token
        self._chat_id = chat_id
        self._client = client

    def send(self, message: str, *, recipient: str | None = None) -> NotificationResult:
        chat_id = recipient or self._chat_id
        if not self._token or not chat_id:
            return NotificationResult(
                success=False,
                provider=self.name,
                error="Telegram notifications are not configured.",
            )
        if not message or not message.strip():
            return NotificationResult(success=False, provider=self.name, error="Message is empty")

        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        chunks = self._chunk_message(message.strip())
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            for chunk in chunks:
                response = client.post(
                    url,
                    json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
                )
                payload = self._safe_json(response)
                
                # Enhanced Logging (No Bot Token)
                logger.info(
                    "Telegram Notification Attempt | Type: Direct Message | "
                    f"Destination Chat ID: {chat_id} | Delivery Status: {response.status_code} | "
                    f"Telegram API Response: {payload}"
                )

                if response.status_code >= 400 or not payload.get("ok", False):
                    description = payload.get("description") or response.text
                    error_msg = f"Telegram API error ({response.status_code}): {description}"
                    logger.error(f"Telegram Notification Failed | Reason: {error_msg}")
                    return NotificationResult(
                        success=False,
                        provider=self.name,
                        error=error_msg,
                    )
            return NotificationResult(success=True, provider=self.name)
        except httpx.HTTPError as exc:
            error_msg = str(exc)
            logger.exception(f"Telegram Notification Failed | Reason: HTTP Exception: {error_msg}")
            return NotificationResult(success=False, provider=self.name, error=error_msg)
        finally:
            if owns_client:
                client.close()

    @staticmethod
    def _chunk_message(message: str) -> list[str]:
        if len(message) <= TELEGRAM_MAX_LENGTH:
            return [message]
        return [message[i : i + TELEGRAM_MAX_LENGTH] for i in range(0, len(message), TELEGRAM_MAX_LENGTH)]

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}
