from urllib.parse import parse_qs, urlparse


def _configure_oura(settings):
    settings.OURA_CLIENT_ID = "oura-client"
    settings.OURA_CLIENT_SECRET = "oura-secret"
    settings.OURA_REDIRECT_URI = "http://testserver/oura/callback"
    settings.OURA_FRONTEND_URL = "/health.html"


def _token_body():
    return {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "scope": "daily workout personal",
    }


def _collections():
    return {
        "daily_activity": [
            {
                "day": "2026-08-01",
                "score": 81,
                "active_calories": 620,
                "total_calories": 2450,
                "steps": 10234,
            }
        ],
        "daily_readiness": [{"day": "2026-08-01", "score": 84}],
        "daily_sleep": [{"day": "2026-08-01", "score": 87}],
        "sleep": [
            {
                "day": "2026-08-01",
                "total_sleep_duration": 27000,
                "average_hrv": 48.5,
                "lowest_heart_rate": 51,
            }
        ],
        "daily_stress": [{"day": "2026-08-01", "stress_high": 3600, "recovery_high": 5400}],
        "workout": [{"day": "2026-08-01", "calories": 410, "duration": 3600}],
    }


def _patch_oura_client(monkeypatch, *, collections=None):
    from backend.app import oura_service

    data = collections or _collections()
    monkeypatch.setattr(oura_service.OuraClient, "exchange_code", lambda self, code: _token_body())
    monkeypatch.setattr(
        oura_service.OuraClient,
        "fetch_personal_info",
        lambda self, token: {"id": "oura-user-1"},
    )
    monkeypatch.setattr(
        oura_service.OuraClient,
        "fetch_collection",
        lambda self, token, endpoint, **kwargs: data.get(endpoint, []),
    )


def _connect_oura(client, headers, monkeypatch, *, collections=None):
    _patch_oura_client(monkeypatch, collections=collections)
    auth_response = client.post("/oura/auth-url", headers=headers)
    assert auth_response.status_code == 200, auth_response.text
    query = parse_qs(urlparse(auth_response.json()["authorization_url"]).query)
    callback_response = client.get(
        "/oura/callback",
        params={"code": "code-123", "state": query["state"][0]},
        follow_redirects=False,
    )
    assert callback_response.status_code in (302, 307)
    assert "oura=connected" in callback_response.headers["location"]


def test_oura_auth_url_requires_configuration(client, register_and_login):
    from backend.app.settings import settings

    settings.OURA_CLIENT_ID = None
    settings.OURA_CLIENT_SECRET = None
    settings.OURA_REDIRECT_URI = None
    headers = register_and_login()

    response = client.post("/oura/auth-url", headers=headers)

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_oura_callback_connects_and_initial_sync_persists_daily_metrics(client, register_and_login, monkeypatch):
    from backend.app.settings import settings

    _configure_oura(settings)
    headers = register_and_login()
    _connect_oura(client, headers, monkeypatch)

    status_response = client.get("/oura/status", headers=headers)
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["connected"] is True
    assert status_payload["synced_days"] == 1
    assert status_payload["latest_readiness"] == 84
    assert status_payload["latest_sleep_score"] == 87

    daily_response = client.get(
        "/oura/daily",
        headers=headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-01"},
    )
    assert daily_response.status_code == 200, daily_response.text
    rows = daily_response.json()
    assert len(rows) == 1
    assert rows[0]["total_calories"] == 2450
    assert rows[0]["steps"] == 10234
    assert rows[0]["average_hrv_ms"] == 48.5
    assert rows[0]["workout_count"] == 1
    assert rows[0]["workout_calories"] == 410.0


def test_health_summary_combines_logged_food_and_oura(client, register_and_login, monkeypatch):
    from backend.app.settings import settings

    _configure_oura(settings)
    headers = register_and_login()
    _connect_oura(client, headers, monkeypatch)

    meal_response = client.post(
        "/me/meals/text",
        headers=headers,
        json={
            "food_description": "fully specified test meal",
            "calories": 1900,
            "protein": 150,
            "fat": 65,
            "carbs": 180,
            "fiber": 30,
            "sugar": 20,
            "sodium": 1500,
            "meal_type": "dinner",
            "consumed_at": "2026-08-01T18:00:00Z",
        },
    )
    assert meal_response.status_code == 200, meal_response.text

    summary_response = client.get(
        "/oura/health-summary",
        headers=headers,
        params={
            "start_date": "2026-08-01",
            "end_date": "2026-08-01",
            "timezone": "Europe/Prague",
            "locale": "cs",
        },
    )
    assert summary_response.status_code == 200, summary_response.text
    payload = summary_response.json()
    assert payload["summary"]["days_with_food"] == 1
    assert payload["summary"]["days_with_oura"] == 1
    assert payload["summary"]["average_energy_balance_kcal"] == -550
    assert payload["days"][0]["nutrition"]["protein_g"] == 150
    assert payload["days"][0]["oura"]["readiness_score"] == 84
    assert payload["days"][0]["energy_balance_kcal"] == -550


def test_oura_data_is_isolated_and_disconnect_removes_local_data(client, register_and_login, monkeypatch):
    from backend.app.settings import settings

    _configure_oura(settings)
    user_one_headers = register_and_login(email="oura-one@example.com")
    user_two_headers = register_and_login(email="oura-two@example.com")
    _connect_oura(client, user_one_headers, monkeypatch)

    user_two_daily = client.get(
        "/oura/daily",
        headers=user_two_headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-01"},
    )
    assert user_two_daily.status_code == 200
    assert user_two_daily.json() == []
    assert client.get("/oura/status", headers=user_two_headers).json()["connected"] is False

    disconnect_response = client.delete("/oura/disconnect", headers=user_one_headers)
    assert disconnect_response.status_code == 204
    assert client.get("/oura/status", headers=user_one_headers).json()["connected"] is False
    user_one_daily = client.get(
        "/oura/daily",
        headers=user_one_headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-01"},
    )
    assert user_one_daily.json() == []
