from __future__ import annotations

import logging

import httpx

from ..config import Settings
from .base import NotificationProvider, NotificationResult

logger = logging.getLogger(__name__)


class WhatsAppNotificationProvider(NotificationProvider):
    """WhatsApp Cloud API provider.

    Uses template messages when WHATSAPP_TEMPLATE_NAME is configured (recommended for
    proactive HR alerts). Falls back to session text messages otherwise.
    """

    name = "whatsapp"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._token = settings.whatsapp_token
        self._to = settings.whatsapp_group_id
        self._phone_number_id = settings.whatsapp_phone_number_id
        self._template_name = settings.whatsapp_template_name
        self._template_language = settings.whatsapp_template_language
        self._api_version = settings.whatsapp_api_version
        self._client = client

    def send(self, message: str, *, recipient: str | None = None) -> NotificationResult:
        to = recipient or self._to
        if not self._token or not to or not self._phone_number_id:
            return NotificationResult(
                success=False,
                provider=self.name,
                error="WhatsApp token, phone number id, or recipient is not configured",
            )
        if not message or not message.strip():
            return NotificationResult(success=False, provider=self.name, error="Message is empty")

        url = f"https://graph.facebook.com/{self._api_version}/{self._phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(to=to, message=message.strip())

        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            response = client.post(url, headers=headers, json=payload)
            body = self._safe_json(response)
            if response.status_code >= 400:
                error = body.get("error", {})
                detail = error.get("message") if isinstance(error, dict) else response.text
                return NotificationResult(
                    success=False,
                    provider=self.name,
                    error=f"WhatsApp API error ({response.status_code}): {detail}",
                )
            if "messages" not in body and "error" in body:
                error = body["error"]
                detail = error.get("message") if isinstance(error, dict) else str(error)
                return NotificationResult(success=False, provider=self.name, error=detail)
            return NotificationResult(success=True, provider=self.name)
        except httpx.HTTPError as exc:
            logger.exception("WhatsApp send failed")
            return NotificationResult(success=False, provider=self.name, error=str(exc))
        finally:
            if owns_client:
                client.close()

    def _build_payload(self, *, to: str, message: str) -> dict:
        if self._template_name:
            return {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": self._template_name,
                    "language": {"code": self._template_language},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": message[:1024]}],
                        }
                    ],
                },
            }
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": message[:4096]},
        }

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}
