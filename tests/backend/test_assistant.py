from datetime import datetime, timezone


def test_assistant_requires_authentication(client):
    response = client.post(
        "/assistant/chat",
        json={"message": "What did I eat today?", "history": [], "timezone": "UTC", "locale": "en"},
    )
    assert response.status_code == 401


def test_assistant_gracefully_handles_missing_openai(client, register_and_login, monkeypatch):
    from backend.app import assistant_service

    headers = register_and_login()
    monkeypatch.setattr(assistant_service, "get_openai_client", lambda: None)

    response = client.post(
        "/assistant/chat",
        headers=headers,
        json={"message": "Summarize my data", "history": [], "timezone": "Europe/Prague", "locale": "en"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["available"] is False
    assert payload["sources"] == []


def test_assistant_tools_are_scoped_to_current_user(client, register_and_login):
    from backend.app import models
    from backend.app.assistant_service import execute_tool
    from backend.app.deps import get_db
    from backend.app.main import app

    register_and_login(email="one@example.com", name="One")
    register_and_login(email="two@example.com", name="Two")

    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user_one = db.query(models.User).filter(models.User.email == "one@example.com").one()
        user_two = db.query(models.User).filter(models.User.email == "two@example.com").one()
        db.add_all(
            [
                models.Meal(
                    user_id=user_one.id,
                    calories=510,
                    protein=34,
                    fat=18,
                    carbs=50,
                    fiber=7,
                    sugar=5,
                    sodium=600,
                    meal_type="lunch",
                    consumed_at=datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
                    notes="User one private meal",
                ),
                models.Meal(
                    user_id=user_two.id,
                    calories=900,
                    protein=10,
                    fat=40,
                    carbs=110,
                    fiber=2,
                    sugar=30,
                    sodium=1200,
                    meal_type="dinner",
                    consumed_at=datetime(2026, 8, 9, 18, 0, tzinfo=timezone.utc),
                    notes="User two private meal",
                ),
            ]
        )
        db.commit()

        result = execute_tool(
            db,
            user_one,
            "get_meals",
            {},
            timezone_name="UTC",
            locale="en",
        )

        assert result["total"] == 1
        assert result["rows"][0]["calories"] == 510
        assert result["rows"][0]["notes"] == "User one private meal"
        assert "User two private meal" not in str(result)
    finally:
        generator.close()


def test_data_inventory_never_exposes_credentials(client, register_and_login):
    from backend.app import models
    from backend.app.assistant_service import execute_tool
    from backend.app.deps import get_db
    from backend.app.main import app

    register_and_login(email="privacy@example.com", name="Privacy")
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user = db.query(models.User).filter(models.User.email == "privacy@example.com").one()
        result = execute_tool(
            db,
            user,
            "get_data_inventory",
            {},
            timezone_name="UTC",
            locale="en",
        )
        serialized = str(result).lower()
        assert "access_token" not in serialized
        assert "refresh_token" not in serialized
        assert "password" not in serialized
        assert "secret" not in serialized
    finally:
        generator.close()
