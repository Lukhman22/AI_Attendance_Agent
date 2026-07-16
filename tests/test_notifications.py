from decimal import Decimal

import httpx

from backend.app.config import Settings
from backend.app.notifications.telegram import TelegramNotificationProvider
from backend.app.notifications.whatsapp import WhatsAppNotificationProvider


def _settings(**kwargs) -> Settings:
    base = dict(
        telegram_token="telegram-token",
        telegram_chat_id="12345",
        whatsapp_token="wa-token",
        whatsapp_group_id="15551234567",
        whatsapp_phone_number_id="phone-id",
        whatsapp_template_name=None,
        whatsapp_template_language="en_US",
        whatsapp_api_version="v19.0",
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


def test_whatsapp_text_and_template_payloads():
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.read().decode())
        return httpx.Response(200, json={"messages": [{"id": "wamid.1"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    text_provider = WhatsAppNotificationProvider(_settings(), client=client)
    assert text_provider.send("Attendance alert").success is True
    assert '"type": "text"' in captured[0] or '"type":"text"' in captured[0].replace(" ", "")

    captured.clear()
    template_provider = WhatsAppNotificationProvider(
        _settings(whatsapp_template_name="hr_alert"),
        client=client,
    )
    assert template_provider.send("Attendance alert").success is True
    assert "template" in captured[0]
    client.close()


def test_providers_fail_without_credentials():
    telegram = TelegramNotificationProvider(Settings.model_construct(telegram_token=None, telegram_chat_id=None))
    whatsapp = WhatsAppNotificationProvider(
        Settings.model_construct(
            whatsapp_token=None,
            whatsapp_group_id=None,
            whatsapp_phone_number_id=None,
            whatsapp_template_name=None,
            whatsapp_template_language="en_US",
            whatsapp_api_version="v19.0",
        )
    )
    assert telegram.send("x").success is False
    assert whatsapp.send("x").success is False
