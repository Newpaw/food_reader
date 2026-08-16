from urllib.parse import parse_qs, urlparse


def _configure_oura(settings):
    settings.OURA_CLIENT_ID = "oura-client"
    settings.OURA_CLIENT_SECRET = "oura-secret"
    settings.OURA_REDIRECT_URI = "http://testserver/oura/callback"
    settings.OURA_FRONTEND_URL = "/health.html"


def _token_body(scope="daily workout personal heartrate tag session spo2Daily"):
    return {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "scope": scope,
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
                "target_calories": 550,
                "average_met_minutes": 1.85,
                "equivalent_walking_distance": 8120,
                "sedentary_time": 27000,
                "resting_time": 30000,
                "low_activity_time": 7200,
                "medium_activity_time": 2400,
                "high_activity_time": 900,
                "non_wear_time": 600,
                "inactivity_alerts": 2,
                "sedentary_met_minutes": 10,
                "low_activity_met_minutes": 120,
                "medium_activity_met_minutes": 90,
                "high_activity_met_minutes": 75,
                "contributors": {
                    "meet_daily_targets": 82,
                    "move_every_hour": 78,
                    "recovery_time": 88,
                    "stay_active": 80,
                    "training_frequency": 84,
                    "training_volume": 79,
                },
            }
        ],
        "daily_readiness": [
            {
                "day": "2026-08-01",
                "score": 84,
                "temperature_deviation": -0.1,
                "temperature_trend_deviation": 0.05,
                "contributors": {
                    "activity_balance": 83,
                    "body_temperature": 92,
                    "hrv_balance": 79,
                    "previous_day_activity": 85,
                    "previous_night": 88,
                    "recovery_index": 81,
                    "resting_heart_rate": 90,
                    "sleep_balance": 86,
                },
            }
        ],
        "daily_sleep": [
            {
                "day": "2026-08-01",
                "score": 87,
                "contributors": {
                    "deep_sleep": 86,
                    "efficiency": 91,
                    "latency": 89,
                    "rem_sleep": 80,
                    "restfulness": 84,
                    "timing": 88,
                    "total_sleep": 90,
                },
            }
        ],
        "sleep": [
            {
                "day": "2026-08-01",
                "total_sleep_duration": 27000,
                "time_in_bed": 28800,
                "awake_time": 1800,
                "light_sleep_duration": 13200,
                "deep_sleep_duration": 5400,
                "rem_sleep_duration": 8400,
                "latency": 720,
                "efficiency": 94,
                "average_hrv": 48.5,
                "lowest_heart_rate": 51,
                "average_heart_rate": 57.2,
                "average_breath": 14.4,
                "bedtime_start": "2026-07-31T22:44:00+02:00",
                "bedtime_end": "2026-08-01T06:44:00+02:00",
                "type": "long_sleep",
                "restless_periods": 14,
            }
        ],
        "daily_stress": [
            {
                "day": "2026-08-01",
                "stress_high": 3600,
                "recovery_high": 5400,
                "day_summary": "restored",
            }
        ],
        "workout": [
            {
                "day": "2026-08-01",
                "activity": "strength_training",
                "label": "Gym",
                "intensity": "moderate",
                "calories": 410,
                "duration": 3600,
                "start_datetime": "2026-08-01T17:00:00+02:00",
                "end_datetime": "2026-08-01T18:00:00+02:00",
            }
        ],
        "daily_spo2": [
            {
                "day": "2026-08-01",
                "spo2_percentage": {"average": 97.2},
            }
        ],
        "daily_resilience": [
            {
                "day": "2026-08-01",
                "level": "solid",
                "contributors": {"sleep_recovery": 0.8, "daytime_recovery": 0.7, "stress": 0.6},
            }
        ],
        "daily_cardiovascular_age": [{"day": "2026-08-01", "vascular_age": 36}],
        "vO2_max": [{"day": "2026-08-01", "vo2_max": 43.7}],
        "session": [
            {
                "day": "2026-08-01",
                "type": "meditation",
                "mood": "good",
                "duration": 600,
                "start_datetime": "2026-08-01T07:00:00+02:00",
                "end_datetime": "2026-08-01T07:10:00+02:00",
            }
        ],
        "enhanced_tag": [
            {
                "day": "2026-08-01",
                "tag_type_code": "alcohol",
                "comment": "test tag",
                "start_time": "2026-08-01T20:00:00+02:00",
            }
        ],
        "heartrate": [
            {"timestamp": "2026-08-01T10:00:00+02:00", "bpm": 62, "source": "awake"},
            {"timestamp": "2026-08-01T10:05:00+02:00", "bpm": 68, "source": "awake"},
            {"timestamp": "2026-08-01T10:10:00+02:00", "bpm": 65, "source": "awake"},
        ],
    }


def _patch_oura_client(monkeypatch, *, collections=None, scope=None):
    from backend.app import oura_service

    data = collections or _collections()
    monkeypatch.setattr(oura_service.OuraClient, "exchange_code", lambda self, code: _token_body(scope or "daily workout personal heartrate tag session spo2Daily"))
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
    monkeypatch.setattr(
        oura_service.OuraClient,
        "fetch_timeseries",
        lambda self, token, endpoint, **kwargs: data.get(endpoint, []),
    )


def _connect_oura(client, headers, monkeypatch, *, collections=None, scope=None):
    _patch_oura_client(monkeypatch, collections=collections, scope=scope)
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


def test_oura_auth_url_requests_richer_scopes(client, register_and_login):
    from backend.app.settings import settings

    _configure_oura(settings)
    headers = register_and_login(email="oura-scopes@example.com")
    response = client.post("/oura/auth-url", headers=headers)
    assert response.status_code == 200
    query = parse_qs(urlparse(response.json()["authorization_url"]).query)
    scopes = set(query["scope"][0].split())
    assert {"daily", "workout", "personal", "heartrate", "tag", "session", "spo2Daily"} <= scopes


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
    assert status_payload["latest_spo2"] == 97.2
    assert status_payload["latest_resilience"] == "solid"
    assert status_payload["needs_reauthorization"] is False

    daily_response = client.get(
        "/oura/daily",
        headers=headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-01"},
    )
    assert daily_response.status_code == 200, daily_response.text
    rows = daily_response.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["total_calories"] == 2450
    assert row["steps"] == 10234
    assert row["activity_target_calories"] == 550
    assert row["sedentary_seconds"] == 27000
    assert row["temperature_deviation_c"] == -0.1
    assert row["deep_sleep_seconds"] == 5400
    assert row["rem_sleep_seconds"] == 8400
    assert row["sleep_efficiency"] == 94.0
    assert row["average_hrv_ms"] == 48.5
    assert row["average_heart_rate_bpm"] == 57.2
    assert row["spo2_average_percent"] == 97.2
    assert row["resilience_level"] == "solid"
    assert row["vascular_age_years"] == 36.0
    assert row["vo2_max"] == 43.7
    assert row["heart_rate_average_bpm"] == 65.0
    assert row["heart_rate_min_bpm"] == 62.0
    assert row["heart_rate_max_bpm"] == 68.0
    assert row["heart_rate_samples"] == 3
    assert row["workout_count"] == 1
    assert row["workout_calories"] == 410.0
    assert row["details"]["readiness_contributors"]["hrv_balance"] == 79
    assert row["details"]["sleep_contributors"]["deep_sleep"] == 86
    assert row["details"]["stress_day_summary"] == "restored"
    assert row["details"]["workouts"][0]["activity"] == "strength_training"
    assert row["details"]["sessions"][0]["type"] == "meditation"
    assert row["details"]["tags"][0]["tag_type_code"] == "alcohol"


def test_existing_oura_connection_reports_missing_richer_scopes(client, register_and_login, monkeypatch):
    from backend.app.settings import settings

    _configure_oura(settings)
    headers = register_and_login(email="oura-old-scope@example.com")
    _connect_oura(client, headers, monkeypatch, scope="daily workout personal")

    status_payload = client.get("/oura/status", headers=headers).json()
    assert status_payload["connected"] is True
    assert status_payload["needs_reauthorization"] is True
    assert {"heartrate", "tag", "session", "spo2Daily"} <= set(status_payload["missing_scopes"])


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
    assert payload["days"][0]["oura"]["deep_sleep_seconds"] == 5400
    assert payload["days"][0]["oura"]["spo2_average_percent"] == 97.2
    assert payload["days"][0]["oura"]["details"]["readiness_contributors"]["sleep_balance"] == 86
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


def test_oura_disconnect_disables_adaptive_calories(client, register_and_login, monkeypatch):
    from backend.app.settings import settings

    _configure_oura(settings)
    headers = register_and_login(email="adaptive-disconnect@example.com")
    profile_response = client.post(
        "/profile",
        headers=headers,
        json={
            "height_cm": 180,
            "weight_kg": 82,
            "age": 31,
            "gender": "male",
            "adaptive_calories_enabled": True,
        },
    )
    assert profile_response.status_code == 201
    _connect_oura(client, headers, monkeypatch)

    disconnect_response = client.delete("/oura/disconnect", headers=headers)
    assert disconnect_response.status_code == 204
    profile = client.get("/profile", headers=headers).json()
    targets = client.get("/profile/targets", headers=headers).json()
    assert profile["adaptive_calories_enabled"] is False
    assert profile["adaptive_target_calories"] is None
    assert targets["adaptive"]["status"] == "disabled"
