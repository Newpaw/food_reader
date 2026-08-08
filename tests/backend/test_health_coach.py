def test_health_coach_context_only_contains_aggregated_numeric_signals():
    from backend.app.health_coach import _compact_context

    summary = {
        "from": "2026-08-01",
        "to": "2026-08-08",
        "summary": {"average_readiness": 82.5, "days_with_food": 8},
        "insights": [{"kind": "energy_balance", "title": "Balance", "detail": "Trend only"}],
        "days": [
            {
                "day": "2026-08-08",
                "nutrition": {
                    "calories": 2100,
                    "protein_g": 155,
                    "last_meal_hour": 20.5,
                    "food_description": "private meal description",
                    "notes": "private meal notes",
                    "image_url": "/uploads/private.jpg",
                },
                "oura": {
                    "readiness_score": 83,
                    "sleep_score": 86,
                    "average_hrv_ms": 47.2,
                    "steps": 9800,
                    "workout_count": 1,
                },
                "energy_balance_kcal": -350,
            }
        ],
    }

    context = _compact_context(summary)
    serialized = str(context)

    assert context["recent_days"][0]["calories"] == 2100
    assert context["recent_days"][0]["readiness"] == 83
    assert "private meal description" not in serialized
    assert "private meal notes" not in serialized
    assert "/uploads/private.jpg" not in serialized


def test_health_coach_returns_safe_fallback_without_openai_key(monkeypatch):
    from backend.app import health_coach

    monkeypatch.setattr(health_coach, "get_openai_client", lambda: None)

    result = health_coach.generate_health_coach(
        {
            "from": "2026-08-01",
            "to": "2026-08-08",
            "summary": {},
            "insights": [],
            "days": [],
        },
        locale="cs",
    )

    assert result["available"] is False
    assert result["confidence"] == "low"
    assert "OpenAI" in result["recommendation"]
