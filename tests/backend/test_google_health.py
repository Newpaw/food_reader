import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from backend.app import google_health_service as service
from backend.app import database
from backend.app.google_health_models import GoogleHealthConnection, GoogleHealthOAuthState, GoogleHealthRecord
from backend.app.settings import settings

DATES = {"start_date": "2026-10-01", "end_date": "2026-10-08"}


@pytest.fixture
def google_config(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_HEALTH_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "GOOGLE_HEALTH_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "GOOGLE_HEALTH_REDIRECT_URI", "http://testserver/google-health/callback")


def oauth_state(client, headers):
    response = client.post("/google-health/auth-url", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "HttpOnly" in response.headers["set-cookie"]
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert not any("write" in scope for scope in query["scope"][0].split())
    return query["state"][0]


def provider(monkeypatch, scopes=None, identity_error=None):
    def fake(url, *, token=None, form=None):
        if url == service.TOKEN_URL:
            return {"access_token": "private-access-token", "refresh_token": "private-refresh-token",
                    "scope": " ".join(scopes or service.SCOPES), "expires_in": 3600}
        if url.endswith("/identity"):
            if identity_error:
                raise service.GoogleHealthError(identity_error)
            return {"healthUserId": "health-user"}
        if "revoke" in url:
            return {}
        return {"dataPoints": []}
    monkeypatch.setattr(service, "request_json", fake)


def connect(client, headers, monkeypatch, scopes=None):
    provider(monkeypatch, scopes=scopes)
    state = oauth_state(client, headers)
    response = client.get("/google-health/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert response.headers["location"] == "/google-health.html?google_health=connected"
    return state


def test_configuration_and_auth_required(client, register_and_login, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_HEALTH_CLIENT_ID", None)
    assert client.get("/google-health/status").status_code == 401
    headers = register_and_login()
    assert client.get("/google-health/status", headers=headers).json()["configured"] is False
    assert client.post("/google-health/auth-url", headers=headers).status_code == 503


def test_oauth_encryption_and_replay(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    state = connect(client, headers, monkeypatch)
    with database.SessionLocal() as db:
        connection = db.query(GoogleHealthConnection).one()
        assert connection.access_token_encrypted != "private-access-token"
        assert service.decrypt_token(connection.refresh_token_encrypted) == "private-refresh-token"
        assert db.query(GoogleHealthOAuthState).count() == 0
    client.cookies.set("google_health_state", state, path="/google-health")
    replay = client.get("/google-health/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert "INVALID_STATE" in replay.headers["location"]
    status = client.get("/google-health/status", headers=headers)
    assert status.json()["connected"] is True
    assert "private-access-token" not in status.text


def test_callback_requires_browser_cookie(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    provider(monkeypatch)
    state = oauth_state(client, headers)
    client.cookies.clear()
    response = client.get("/google-health/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert "INVALID_STATE" in response.headers["location"]
    assert client.get("/google-health/status", headers=headers).json()["connected"] is False


def test_expired_state(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    provider(monkeypatch)
    state = oauth_state(client, headers)
    with database.SessionLocal() as db:
        row = db.get(GoogleHealthOAuthState, hashlib.sha256(state.encode()).hexdigest())
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    response = client.get("/google-health/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert "INVALID_STATE" in response.headers["location"]


@pytest.mark.parametrize("reason", ["ACCOUNT_NOT_LINKED", "MISSING_PERMISSIONS"])
def test_failed_link_does_not_mark_connected(client, register_and_login, google_config, monkeypatch, reason):
    headers = register_and_login()
    if reason == "ACCOUNT_NOT_LINKED":
        provider(monkeypatch, identity_error=reason)
    else:
        monkeypatch.setattr(service, "request_json", lambda *args, **kwargs: {"access_token": "token", "scope": ""})
    state = oauth_state(client, headers)
    response = client.get("/google-health/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert reason in response.headers["location"]
    assert client.get("/google-health/status", headers=headers).json()["connected"] is False


def test_partial_consent_and_idempotent_sync(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    connect(client, headers, monkeypatch, [service.SCOPE_BASE + "activity_and_fitness.readonly"])
    calls = []
    def fake(url, **kwargs):
        calls.append(url)
        if "/steps/" in url:
            return {"dataPoints": [steps_point("60"), steps_point("60")]}
        return {"dataPoints": []}
    monkeypatch.setattr(service, "request_json", fake)
    for _ in range(2):
        response = client.post("/google-health/sync", headers=headers, params=DATES)
        assert response.status_code == 200, response.text
        assert response.json()["synced"]["steps"] == 1
        assert response.json()["warnings"]["sleep"] == "MISSING_PERMISSIONS"
    assert all("/sleep/" not in url for url in calls)
    data = client.get("/google-health/data", headers=headers, params=DATES)
    assert data.headers["cache-control"] == "no-store"
    assert data.json()["daily"] == [{"day": "2026-10-08", "steps": 60}]
    export = client.get("/google-health/export", headers=headers, params=DATES)
    assert "attachment" in export.headers["content-disposition"]
    assert export.json() == data.json()
    other_headers = register_and_login(email="other@example.com")
    assert client.get("/google-health/data", headers=other_headers, params=DATES).json()["records"] == []


def steps_point(count="0"):
    return {"dataPointName": "users/me/dataTypes/steps/dataPoints/1", "steps": {"count": count,
            "interval": {"startTime": "2026-10-08T10:00:00Z", "endTime": "2026-10-08T10:01:00Z",
                         "civilStartTime": {"date": {"year": 2026, "month": 10, "day": 8}}}}}


def test_pagination_and_range_filter(monkeypatch):
    calls = []
    def fake(url, **kwargs):
        query = parse_qs(urlparse(url).query)
        calls.append(query)
        if len(calls) == 1:
            return {"dataPoints": [steps_point()], "nextPageToken": "second-page"}
        return {"dataPoints": [steps_point("10")]}
    monkeypatch.setattr(service, "request_json", fake)
    assert len(service.fetch_records("token", "steps", date(2026, 10, 1), date(2026, 10, 8))) == 2
    assert calls[1]["pageToken"] == ["second-page"]
    assert 'steps.interval.civil_start_time < "2026-10-09"' in calls[0]["filter"][0]


def test_failed_page_preserves_existing_data(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    connect(client, headers, monkeypatch)
    monkeypatch.setattr(service, "fetch_records", lambda token, kind, start, end: [steps_point("100")] if kind == "steps" else [])
    assert client.post("/google-health/sync", headers=headers, params=DATES).status_code == 200
    def fail(token, kind, start, end):
        if kind == "steps":
            raise service.GoogleHealthError("PROVIDER_UNAVAILABLE", 502)
        return []
    monkeypatch.setattr(service, "fetch_records", fail)
    response = client.post("/google-health/sync", headers=headers, params=DATES)
    assert response.json()["warnings"]["steps"] == "PROVIDER_UNAVAILABLE"
    assert client.get("/google-health/data", headers=headers, params=DATES).json()["daily"][0]["steps"] == 100
    monkeypatch.setattr(service, "fetch_records", lambda *args: [])
    client.post("/google-health/sync", headers=headers, params=DATES)
    assert client.get("/google-health/data", headers=headers, params=DATES).json()["daily"] == []


def test_refresh_and_disconnect(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    connect(client, headers, monkeypatch)
    with database.SessionLocal() as db:
        connection = db.query(GoogleHealthConnection).one()
        connection.token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        assert service.access_token(db, connection) == "private-access-token"
    assert client.delete("/google-health/disconnect", headers=headers).status_code == 204
    assert client.get("/google-health/status", headers=headers).json()["connected"] is False
    with database.SessionLocal() as db:
        assert db.query(GoogleHealthRecord).count() == 0


def test_invalid_refresh_requires_reconnect(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    connect(client, headers, monkeypatch)
    with database.SessionLocal() as db:
        row = db.query(GoogleHealthConnection).one()
        row.token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    def fail(*args, **kwargs):
        raise service.GoogleHealthError("invalid_grant", 400)
    monkeypatch.setattr(service, "request_json", fail)
    response = client.post("/google-health/sync", headers=headers, params=DATES)
    assert response.status_code == 409
    assert response.json()["detail"] == "RECONNECT_REQUIRED"


@pytest.mark.parametrize("start,end", [("2026-10-08", "2026-10-01"), ("2026-01-01", "2026-10-08")])
def test_invalid_date_range(client, register_and_login, start, end):
    headers = register_and_login()
    assert client.get("/google-health/data", headers=headers, params={"start_date": start, "end_date": end}).status_code == 422


def test_local_dates_and_units():
    point = {"weight": {"weightGrams": 81250, "sampleTime": {"physicalTime": "2026-10-07T23:30:00Z", "utcOffset": "7200s"}}}
    assert service.record_day(point, "weight") == "2026-10-08"
    rows = [GoogleHealthRecord(day="2026-10-08", data_type="weight", payload_json=json.dumps(point)),
            GoogleHealthRecord(day="2026-10-08", data_type="steps", payload_json=json.dumps(steps_point()))]
    assert service.daily_summary(rows) == [{"day": "2026-10-08", "weight_kg": 81.25, "steps": 0}]


def test_reauthorization_replaces_account_and_removes_old_records(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    connect(client, headers, monkeypatch)
    with database.SessionLocal() as db:
        user_id = db.query(GoogleHealthConnection).one().user_id
        db.add(GoogleHealthRecord(user_id=user_id, day="2026-10-08", data_type="steps", record_key="old", payload_json=json.dumps(steps_point())))
        db.commit()
    state = oauth_state(client, headers)
    def other_account(url, **kwargs):
        if url == service.TOKEN_URL:
            return {"access_token": "new-access", "refresh_token": "new-refresh", "scope": " ".join(service.SCOPES)}
        return {"healthUserId": "different-account"}
    monkeypatch.setattr(service, "request_json", other_account)
    response = client.get("/google-health/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert "connected" in response.headers["location"]
    assert client.get("/google-health/data", headers=headers, params=DATES).json()["records"] == []


def test_malformed_sync_preserves_data(client, register_and_login, google_config, monkeypatch):
    headers = register_and_login()
    connect(client, headers, monkeypatch)
    monkeypatch.setattr(service, "fetch_records", lambda token, kind, start, end: [steps_point("100")] if kind == "steps" else [])
    client.post("/google-health/sync", headers=headers, params=DATES)
    monkeypatch.setattr(service, "fetch_records", lambda token, kind, start, end: [steps_point("invalid")] if kind == "steps" else [])
    result = client.post("/google-health/sync", headers=headers, params=DATES)
    assert result.json()["warnings"]["steps"] == "INVALID_PROVIDER_DATA"
    assert client.get("/google-health/data", headers=headers, params=DATES).json()["daily"][0]["steps"] == 100


def test_provider_error_is_sanitized(monkeypatch):
    import io
    from urllib.error import HTTPError
    def fail(*args, **kwargs):
        raise HTTPError("https://health.googleapis.com", 400, "bad", {}, io.BytesIO(json.dumps({"error": {
            "message": "secret token must not escape", "details": [{"reason": "ACCOUNT_NOT_LINKED"}]
        }}).encode()))
    monkeypatch.setattr(service, "urlopen", fail)
    with pytest.raises(service.GoogleHealthError, match="ACCOUNT_NOT_LINKED") as caught:
        service.request_json(service.API_BASE + "/identity", token="secret-token")
    assert "secret" not in str(caught.value)


def test_revocation_accepts_empty_success(monkeypatch):
    import io
    monkeypatch.setattr(service, "urlopen", lambda *args, **kwargs: io.BytesIO(b""))
    assert service.request_json("https://oauth2.googleapis.com/revoke", form={"token": "test"}) == {}


def test_hrv_and_sleep_units():
    rows = [GoogleHealthRecord(day="2026-10-08", data_type="sleep", payload_json=json.dumps({"sleep": {"summary": {"minutesAsleep": "450"}}})),
            GoogleHealthRecord(day="2026-10-08", data_type="daily-heart-rate-variability", payload_json=json.dumps({"dailyHeartRateVariability": {"averageHeartRateVariabilityMilliseconds": 42.5}}))]
    assert service.daily_summary(rows) == [{"day": "2026-10-08", "sleep_minutes": 450, "hrv_ms": 42.5}]


def test_additive_migration():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect
    from backend.app.models import User
    path = Path(__file__).resolve().parents[2] / "calorie-tracker/alembic/versions/008_add_google_health.py"
    spec = importlib.util.spec_from_file_location("google_health_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert "google_health_connections" in inspect(connection).get_table_names()
        assert "payload_json" in {column["name"] for column in inspect(connection).get_columns("google_health_records")}
        migration.downgrade()
        assert inspect(connection).get_table_names() == ["users"]
