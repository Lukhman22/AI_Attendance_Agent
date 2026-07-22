from decimal import Decimal

import httpx

from backend.app.config import Settings
from backend.app.notifications.telegram import TelegramNotificationProvider


def _settings(**kwargs) -> Settings:
    base = dict(
        telegram_token="telegram-token",
        telegram_chat_id="12345",
    )
    base.update(kwargs)
    return Settings.model_construct(**base)


def test_telegram_provider_sends_real_api_payload():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = TelegramNotificationProvider(_settings(), client=client)
    result = provider.send("Daily HR summary ready")
    assert result.success is True
    assert len(calls) == 1
    assert "sendMessage" in str(calls[0].url)
    assert b"Daily HR summary ready" in calls[0].content
    client.close()


def test_telegram_provider_surfaces_api_errors():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = TelegramNotificationProvider(_settings(), client=client)
    result = provider.send("Hello")
    assert result.success is False
    assert "chat not found" in (result.error or "")
    client.close()





def test_providers_fail_without_credentials():
    telegram = TelegramNotificationProvider(Settings.model_construct(telegram_token=None, telegram_chat_id=None))
    assert telegram.send("x").success is False
