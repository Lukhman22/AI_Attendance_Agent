from __future__ import annotations

import logging

import httpx

from ..config import Settings
from .base import NotificationProvider, NotificationResult

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096


class TelegramNotificationProvider(NotificationProvider):
    name = "telegram"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._token = settings.telegram_token
        self._chat_id = settings.telegram_chat_id
        self._client = client

    def send(self, message: str, *, recipient: str | None = None) -> NotificationResult:
        chat_id = recipient or self._chat_id
        if not self._token or not chat_id:
            return NotificationResult(
                success=False,
                provider=self.name,
                error="Telegram token or chat id is not configured",
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
                if response.status_code >= 400 or not payload.get("ok", False):
                    description = payload.get("description") or response.text
                    return NotificationResult(
                        success=False,
                        provider=self.name,
                        error=f"Telegram API error ({response.status_code}): {description}",
                    )
            return NotificationResult(success=True, provider=self.name)
        except httpx.HTTPError as exc:
            logger.exception("Telegram send failed")
            return NotificationResult(success=False, provider=self.name, error=str(exc))
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
