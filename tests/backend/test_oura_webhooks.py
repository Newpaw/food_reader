import hashlib
import hmac
import json


def test_oura_webhook_verification_and_signed_event(client, monkeypatch):
    from backend.app.routers import oura_webhook_router
    from backend.app.settings import settings
    from backend.app.oura_webhook_service import oura_webhook_verification_token

    monkeypatch.setattr(settings, "OURA_CLIENT_SECRET", "oura-secret")
    monkeypatch.setattr(settings, "OURA_WEBHOOK_VERIFICATION_TOKEN", "verify-me")

    verification = client.get(
        "/oura/webhook",
        params={"verification_token": oura_webhook_verification_token(), "challenge": "challenge-123"},
    )
    assert verification.status_code == 200
    assert verification.json() == {"challenge": "challenge-123"}

    rejected = client.get(
        "/oura/webhook",
        params={"verification_token": "wrong", "challenge": "challenge-123"},
    )
    assert rejected.status_code == 401

    received = []
    monkeypatch.setattr(oura_webhook_router, "process_oura_webhook_event", lambda payload: received.append(payload))

    payload = {
        "event_type": "update",
        "data_type": "daily_readiness",
        "object_id": "readiness-1",
        "user_id": "oura-user-1",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = "1788984000"
    signature = hmac.new(
        b"oura-secret",
        timestamp.encode("utf-8") + raw,
        hashlib.sha256,
    ).hexdigest().upper()

    response = client.post(
        "/oura/webhook",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-oura-timestamp": timestamp,
            "x-oura-signature": signature,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "accepted"}
    assert received == [payload]


def test_reconcile_creates_missing_oura_subscriptions(monkeypatch):
    from backend.app import oura_webhook_service as service
    from backend.app.settings import settings

    monkeypatch.setattr(settings, "OURA_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "OURA_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "OURA_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "MCP_PUBLIC_BASE_URL", "https://food.example.com")
    monkeypatch.setattr(settings, "OURA_WEBHOOK_CALLBACK_URL", None)
    monkeypatch.setattr(settings, "OURA_WEBHOOK_DATA_TYPES", "daily_activity,daily_readiness")
    monkeypatch.setattr(settings, "OURA_WEBHOOK_EVENT_TYPES", "create,update")

    monkeypatch.setattr(service, "list_webhook_subscriptions", lambda: [])
    created = []
    monkeypatch.setattr(
        service,
        "create_webhook_subscription",
        lambda data_type, event_type: created.append((data_type, event_type)) or {"id": "new"},
    )

    result = service.reconcile_webhook_subscriptions()
    assert result["enabled"] is True
    assert result["desired_subscriptions"] == 4
    assert result["created"] == 4
    assert set(created) == {
        ("daily_activity", "create"),
        ("daily_activity", "update"),
        ("daily_readiness", "create"),
        ("daily_readiness", "update"),
    }
