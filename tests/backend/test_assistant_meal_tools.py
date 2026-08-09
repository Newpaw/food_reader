from datetime import datetime, timezone


def _db_and_user(register_and_login, email: str, name: str = "Meal Tool"):
    from backend.app import models
    from backend.app.deps import get_db
    from backend.app.main import app

    register_and_login(email=email, name=name)
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    user = db.query(models.User).filter(models.User.email == email).one()
    return generator, db, user


def test_add_meal_tool_uses_existing_text_analyzer(register_and_login, monkeypatch):
    from backend.app import assistant_meal_tools, models

    generator, db, user = _db_and_user(register_and_login, "meal-add@example.com")
    try:
        monkeypatch.setattr(
            assistant_meal_tools,
            "get_meal_data_from_text",
            lambda description: (
                620,
                42,
                21,
                64,
                8,
                7,
                710,
                "lunch",
                datetime(2026, 8, 9, 12, 30, tzinfo=timezone.utc),
                "Estimated from text",
            ),
        )

        result = assistant_meal_tools.execute_meal_mutation_tool(
            db,
            user,
            "add_meal",
            {"food_description": "Dva rohlíky se šunkou a sýrem a skyr"},
            timezone_name="Europe/Prague",
        )

        assert result["created"] is True
        assert result["meal"]["calories"] == 620
        assert result["meal"]["protein"] == 42
        meal = db.query(models.Meal).filter(models.Meal.id == result["meal"]["id"]).one()
        assert meal.user_id == user.id
        assert meal.is_text_only is True
        assert "Dva rohlíky" in meal.notes
    finally:
        generator.close()


def test_update_and_delete_meal_tools_are_scoped_to_current_user(register_and_login):
    from backend.app import assistant_meal_tools, models
    from backend.app.deps import get_db
    from backend.app.main import app

    register_and_login(email="meal-one@example.com", name="One")
    register_and_login(email="meal-two@example.com", name="Two")
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        user_one = db.query(models.User).filter(models.User.email == "meal-one@example.com").one()
        user_two = db.query(models.User).filter(models.User.email == "meal-two@example.com").one()
        meal_one = models.Meal(
            user_id=user_one.id,
            calories=500,
            protein=30,
            fat=15,
            carbs=55,
            fiber=6,
            sugar=5,
            sodium=500,
            meal_type="lunch",
            consumed_at=datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
            notes="Original",
            is_text_only=True,
        )
        meal_two = models.Meal(
            user_id=user_two.id,
            calories=800,
            protein=25,
            fat=35,
            carbs=90,
            fiber=4,
            sugar=12,
            sodium=900,
            meal_type="dinner",
            consumed_at=datetime(2026, 8, 9, 18, 0, tzinfo=timezone.utc),
            notes="Private other-user meal",
            is_text_only=True,
        )
        db.add_all([meal_one, meal_two])
        db.commit()
        db.refresh(meal_one)
        db.refresh(meal_two)

        updated = assistant_meal_tools.execute_meal_mutation_tool(
            db,
            user_one,
            "update_meal",
            {"meal_id": meal_one.id, "calories": 550, "protein": 35},
            timezone_name="UTC",
        )
        assert updated["updated"] is True
        assert updated["meal"]["calories"] == 550
        assert updated["meal"]["protein"] == 35

        forbidden_update = assistant_meal_tools.execute_meal_mutation_tool(
            db,
            user_one,
            "update_meal",
            {"meal_id": meal_two.id, "calories": 1},
            timezone_name="UTC",
        )
        assert "error" in forbidden_update
        assert db.query(models.Meal).filter(models.Meal.id == meal_two.id).one().calories == 800

        forbidden_delete = assistant_meal_tools.execute_meal_mutation_tool(
            db,
            user_one,
            "delete_meal",
            {"meal_id": meal_two.id},
            timezone_name="UTC",
        )
        assert "error" in forbidden_delete
        assert db.query(models.Meal).filter(models.Meal.id == meal_two.id).one() is not None

        deleted = assistant_meal_tools.execute_meal_mutation_tool(
            db,
            user_one,
            "delete_meal",
            {"meal_id": meal_one.id},
            timezone_name="UTC",
        )
        assert deleted["deleted"] is True
        assert db.query(models.Meal).filter(models.Meal.id == meal_one.id).first() is None
    finally:
        generator.close()
