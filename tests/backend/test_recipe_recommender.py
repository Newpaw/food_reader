import json
from types import SimpleNamespace


def _summary(*, meals=2, oura=True):
    return {
        "targets": {
            "calories": 2400,
            "protein_g": 180,
            "carbs_g": 260,
            "fat_g": 80,
            "fiber_g": 32,
            "goal": "weight_loss",
            "dietary_preference": "high_protein",
        },
        "days": [
            {
                "day": "2026-08-15",
                "nutrition": {
                    "calories": 1500 if meals else 0,
                    "protein_g": 110 if meals else 0,
                    "carbs_g": 150 if meals else 0,
                    "fat_g": 50 if meals else 0,
                    "fiber_g": 18 if meals else 0,
                    "meal_count": meals,
                    "last_meal_hour": 14.0 if meals else None,
                },
                "oura": None
                if not oura
                else {
                    "steps": 8200,
                    "active_calories": 540,
                    "total_calories": 2200,
                    "readiness_score": 81,
                    "sleep_score": 84,
                    "workout_count": 1,
                    "workout_calories": 310,
                    "workout_seconds": 2700,
                },
            }
        ],
    }


def test_recipe_endpoint_requires_authentication(client):
    response = client.post(
        "/assistant/recipe",
        json={"timezone": "Europe/Prague", "locale": "cs"},
    )
    assert response.status_code == 401


def test_recipe_recommendation_uses_remaining_day_and_oura(monkeypatch):
    from backend.app import recipe_recommender

    monkeypatch.setattr(recipe_recommender, "build_health_summary", lambda *args, **kwargs: _summary())

    calls = []
    recipe_json = {
        "title": "Kuřecí bowl se skyrem",
        "why": "Doplní hlavně protein a nechá rezervu na později.",
        "prep_minutes": 10,
        "cook_minutes": 15,
        "ingredients": [
            {"item": "kuřecí prsa", "amount": "180 g"},
            {"item": "rýže", "amount": "70 g suché"},
            {"item": "skyr", "amount": "100 g"},
        ],
        "steps": ["Uvař rýži.", "Opeč kuře a smíchej se skyrem."],
        "macros": {"calories": 620, "protein_g": 65, "carbs_g": 68, "fat_g": 12, "fiber_g": 5},
        "confidence": "high",
    }

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(recipe_json, ensure_ascii=False)))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(recipe_recommender, "get_openai_client", lambda: fake_client)

    result = recipe_recommender.generate_recipe_recommendation(
        object(),
        SimpleNamespace(id=7),
        timezone_name="Europe/Prague",
        locale="cs",
    )

    assert result["available"] is True
    assert result["context"]["remaining"]["calories"] == 900
    assert result["context"]["remaining"]["protein_g"] == 70
    assert result["context"]["oura"]["steps"] == 8200
    assert result["recipe"]["title"] == "Kuřecí bowl se skyrem"
    assert result["recipe"]["macros"]["protein_g"] == 65
    assert len(calls) == 1
    assert "remaining" in calls[0]["messages"][1]["content"]
    assert "readiness_score" in calls[0]["messages"][1]["content"]


def test_recipe_requires_existing_food_log(monkeypatch):
    from backend.app import recipe_recommender

    monkeypatch.setattr(recipe_recommender, "build_health_summary", lambda *args, **kwargs: _summary(meals=0, oura=False))

    def should_not_call_openai():
        raise AssertionError("OpenAI must not be called before today's food is logged")

    monkeypatch.setattr(recipe_recommender, "get_openai_client", should_not_call_openai)

    result = recipe_recommender.generate_recipe_recommendation(
        object(),
        SimpleNamespace(id=7),
        timezone_name="Europe/Prague",
        locale="cs",
    )

    assert result["available"] is False
    assert result["recipe"] is None
    assert "Nejdřív zapiš" in result["message"]
