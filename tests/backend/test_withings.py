from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse


def _configure_withings(settings):
    settings.WITHINGS_CLIENT_ID = "withings-client"
    settings.WITHINGS_CLIENT_SECRET = "withings-secret"
    settings.WITHINGS_REDIRECT_URI = "http://testserver/withings/callback"
    settings.APP_FRONTEND_URL = "/profile.html"


def _token_body():
    return {
        "userid": "withings-user-1",
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "scope": "user.metrics",
    }


def _measure_group(grpid, measured_at, modified_at, weight_grams):
    return {
        "grpid": grpid,
        "attrib": 0,
        "date": int(measured_at.timestamp()),
        "created": int(measured_at.timestamp()),
        "modified": int(modified_at.timestamp()),
        "category": 1,
        "deviceid": "device-1",
        "model": "Body+",
        "measures": [
            {"type": 1, "value": weight_grams, "unit": -3},
            {"type": 6, "value": 223, "unit": -1},
            {"type": 76, "value": 61000, "unit": -3},
        ],
    }


def _connect_withings(client, headers, monkeypatch):
    from backend.app import withings_service

    monkeypatch.setattr(withings_service.WithingsClient, "exchange_code", lambda self, code: _token_body())
    auth_response = client.post("/withings/auth-url", headers=headers)
    assert auth_response.status_code == 200, auth_response.text
    query = parse_qs(urlparse(auth_response.json()["authorization_url"]).query)
    callback_response = client.get(
        "/withings/callback",
        params={"code": "code-123", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert callback_response.status_code in (302, 307)


def test_withings_auth_url_requires_configuration(client, register_and_login):
    from backend.app.settings import settings

    settings.WITHINGS_CLIENT_ID = None
    settings.WITHINGS_CLIENT_SECRET = None
    settings.WITHINGS_REDIRECT_URI = None
    headers = register_and_login()

    response = client.post("/withings/auth-url", headers=headers)

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_withings_callback_connects_account_and_rejects_bad_state(client, register_and_login, monkeypatch):
    from backend.app.settings import settings

    _configure_withings(settings)
    headers = register_and_login()

    bad_state_response = client.get(
        "/withings/callback",
        params={"code": "code-123", "state": "bad-state"},
        follow_redirects=False,
    )
    assert "authorization_failed" in bad_state_response.headers["location"]

    _connect_withings(client, headers, monkeypatch)

    status_response = client.get("/withings/status", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["connected"] is True
    assert status_response.json()["scope"] == "user.metrics"


def test_withings_client_paginates_measure_groups(monkeypatch):
    from backend.app.withings_service import WithingsClient

    calls = []
    first = _measure_group(1, datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc), 82000)
    second = _measure_group(2, datetime(2026, 1, 3, tzinfo=timezone.utc), datetime(2026, 1, 4, tzinfo=timezone.utc), 81000)

    def fake_post_form(self, url, data, **kwargs):
        calls.append(data)
        if data.get("offset") is None:
            return {"status": 0, "body": {"measuregrps": [first], "more": 1, "offset": 42}}
        return {"status": 0, "body": {"measuregrps": [second], "more": 0}}

    monkeypatch.setattr(WithingsClient, "_post_form", fake_post_form)

    groups = WithingsClient().get_measure_groups("access-token", lastupdate=10)

    assert [group["grpid"] for group in groups] == [1, 2]
    assert calls[0]["lastupdate"] == 10
    assert calls[1]["offset"] == 42


def test_withings_sync_upserts_measurements_and_updates_profile(client, register_and_login, monkeypatch):
    from backend.app import withings_service
    from backend.app.settings import settings

    _configure_withings(settings)
    headers = register_and_login()
    profile_response = client.post(
        "/profile",
        headers=headers,
        json={
            "height_cm": 180,
            "weight_kg": 82,
            "age": 31,
            "gender": "male",
            "activity_level": "moderately_active",
            "goal": "maintenance",
        },
    )
    assert profile_response.status_code == 201
    _connect_withings(client, headers, monkeypatch)

    groups = [
        _measure_group(101, datetime(2026, 5, 1, tzinfo=timezone.utc), datetime(2026, 5, 2, tzinfo=timezone.utc), 82300),
        _measure_group(102, datetime(2026, 5, 5, tzinfo=timezone.utc), datetime(2026, 5, 6, tzinfo=timezone.utc), 81100),
    ]
    monkeypatch.setattr(withings_service.WithingsClient, "get_measure_groups", lambda self, token, **kwargs: groups)

    sync_response = client.post("/withings/sync", headers=headers)

    assert sync_response.status_code == 200, sync_response.text
    payload = sync_response.json()
    assert payload["synced_count"] == 2
    assert payload["latest_weight_kg"] == 81.1
    assert payload["profile_weight_updated"] is True

    profile = client.get("/profile", headers=headers).json()
    assert profile["weight_kg"] == 81.1
    assert profile["weight_source"] == "withings"
    assert profile["weight_measured_at"].startswith("2026-05-05")

    targets = client.get("/profile/targets", headers=headers).json()
    assert targets["calories"] > 0


def test_withings_measurements_filter_disconnect_and_user_isolation(client, register_and_login, monkeypatch):
    from backend.app import withings_service
    from backend.app.settings import settings

    _configure_withings(settings)
    user_one_headers = register_and_login(email="one@example.com")
    user_two_headers = register_and_login(email="two@example.com")
    _connect_withings(client, user_one_headers, monkeypatch)

    groups = [
        _measure_group(201, datetime(2026, 4, 1, tzinfo=timezone.utc), datetime(2026, 4, 2, tzinfo=timezone.utc), 84000),
        _measure_group(202, datetime(2026, 6, 1, tzinfo=timezone.utc), datetime(2026, 6, 2, tzinfo=timezone.utc), 80000),
    ]
    monkeypatch.setattr(withings_service.WithingsClient, "get_measure_groups", lambda self, token, **kwargs: groups)
    assert client.post("/withings/sync", headers=user_one_headers).status_code == 200

    filtered = client.get(
        "/withings/measurements",
        headers=user_one_headers,
        params={
            "frm": "2026-05-01T00:00:00Z",
            "to": "2026-07-01T00:00:00Z",
        },
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["withings_grpid"] == "202"

    isolated = client.get("/withings/measurements", headers=user_two_headers)
    assert isolated.status_code == 200
    assert isolated.json() == []

    disconnect = client.delete("/withings/disconnect", headers=user_one_headers)
    assert disconnect.status_code == 204
    assert client.get("/withings/measurements", headers=user_one_headers).json() == []
    assert client.get("/withings/status", headers=user_one_headers).json()["connected"] is False
