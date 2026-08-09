def test_responses_api_exposes_all_meal_mutation_tools():
    from backend.app.assistant_responses_service import _response_tools

    names = {tool["name"] for tool in _response_tools()}
    assert {"add_meal", "update_meal", "delete_meal"}.issubset(names)


def test_runtime_instructions_define_safe_meal_write_rules():
    from backend.app import models
    from backend.app.assistant_responses_service import _runtime_instructions

    user = models.User(name="Test", email="test-write@example.com", password_hash="x")
    instructions = _runtime_instructions(
        user,
        timezone_name="Europe/Prague",
        locale="cs",
        inventory={"meals": {"count": 1, "last": "2026-08-09T12:00:00+00:00"}},
    )

    assert "Meal logging exception to the base read-only rule" in instructions
    assert "Do not log hypothetical, planned, recommended, or merely discussed food" in instructions
    assert "Use get_meals first whenever needed to identify the exact meal_id" in instructions
    assert "Never create duplicate meal records" in instructions
