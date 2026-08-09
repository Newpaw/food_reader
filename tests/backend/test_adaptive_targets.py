from datetime import date, timedelta

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _session():
    from backend.app.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _profile(db, *, email="adaptive@example.com", enabled=True, custom_calories=None):
    from backend.app import models

    user = models.User(name="Adaptive", email=email, password_hash="x")
    db.add(user)
    db.flush()
    profile = models.UserProfile(
        user_id=user.id,
        height_cm=180,
        weight_kg=80,
        age=35,
        gender="male",
        activity_level="sedentary",
        goal="maintenance",
        dietary_preference="none",
        bmr=1700,
        tdee=2000,
        target_calories=custom_calories or 2000,
        target_protein_g=150,
        target_carbs_g=200,
        target_fats_g=67,
        target_fiber_g=30,
        custom_calories=custom_calories,
        adaptive_calories_enabled=enabled,
    )
    db.add(profile)
    db.commit()
    return user, profile


def _connect(db, user_id):
    from backend.app.oura_models import OuraConnection

    db.add(
        OuraConnection(
            user_id=user_id,
            access_token_encrypted="access",
            refresh_token_encrypted="refresh",
        )
    )
    db.commit()


def _add_burns(db, user_id, today, offsets, burn):
    from backend.app.oura_models import OuraDailyMetric

    for offset in offsets:
        db.add(
            OuraDailyMetric(
                user_id=user_id,
                day=(today - timedelta(days=offset)).isoformat(),
                total_calories=burn,
            )
        )
    db.commit()


def test_adaptive_target_falls_back_when_disabled_or_not_connected():
    from backend.app.adaptive_targets import resolve_nutrition_targets

    db = _session()
    user, profile = _profile(db, enabled=False)

    disabled = resolve_nutrition_targets(db, user.id, today=date(2026, 8, 9))
    assert disabled.calories == disabled.base_calories == 2000
    assert disabled.adaptive.status == "disabled"

    profile.adaptive_calories_enabled = True
    db.commit()
    disconnected = resolve_nutrition_targets(db, user.id, today=date(2026, 8, 9))
    assert disconnected.calories == 2000
    assert disconnected.adaptive.status == "not_connected"


def test_adaptive_target_requires_enough_fresh_completed_days():
    from backend.app.adaptive_targets import resolve_nutrition_targets

    today = date(2026, 8, 9)
    db = _session()
    user, _ = _profile(db)
    _connect(db, user.id)
    _add_burns(db, user.id, today, range(1, 10), 2400)

    warming = resolve_nutrition_targets(db, user.id, today=today)
    assert warming.adaptive.status == "warming_up"
    assert warming.adaptive.data_days == 9
    assert warming.calories == 2000

    from backend.app.oura_models import OuraDailyMetric

    db.query(OuraDailyMetric).delete()
    db.commit()
    _add_burns(db, user.id, today, range(3, 13), 2400)
    stale = resolve_nutrition_targets(db, user.id, today=today)
    assert stale.adaptive.status == "stale"
    assert stale.adaptive.data_days == 10
    assert stale.calories == 2000


def test_adaptive_target_excludes_today_caps_and_smooths_changes():
    from backend.app.adaptive_targets import refresh_adaptive_target, resolve_nutrition_targets
    from backend.app.oura_models import OuraDailyMetric

    today = date(2026, 8, 9)
    db = _session()
    user, profile = _profile(db)
    _connect(db, user.id)
    _add_burns(db, user.id, today, range(1, 11), 4000)
    db.add(OuraDailyMetric(user_id=user.id, day=today.isoformat(), total_calories=100))
    db.commit()

    first = refresh_adaptive_target(db, user.id, today=today)
    assert first.adaptive.status == "active"
    assert first.adaptive.burn_baseline == 4000
    assert first.calories == 2100
    assert first.adaptive.adjustment_kcal == 100
    assert first.protein_g == 150
    assert first.fiber_g == 30
    assert first.carbs_g > 200
    assert first.fats_g > 67

    same_day = refresh_adaptive_target(db, user.id, today=today)
    assert same_day.calories == 2100
    second_day = refresh_adaptive_target(db, user.id, today=today + timedelta(days=1))
    assert second_day.calories == 2200
    third_day = refresh_adaptive_target(db, user.id, today=today + timedelta(days=2))
    assert third_day.calories == 2250
    assert third_day.adaptive.recommended_min_calories == 2150
    assert third_day.adaptive.recommended_max_calories == 2350

    db.refresh(profile)
    assert profile.adaptive_target_calories == 2250
    assert profile.adaptive_target_updated_on == today + timedelta(days=2)
    assert resolve_nutrition_targets(db, user.id, today=today + timedelta(days=2)).calories == 2250


def test_custom_calorie_override_wins_over_oura_data():
    from backend.app.adaptive_targets import resolve_nutrition_targets

    today = date(2026, 8, 9)
    db = _session()
    user, _ = _profile(db, custom_calories=2300)
    _connect(db, user.id)
    _add_burns(db, user.id, today, range(1, 11), 4000)

    targets = resolve_nutrition_targets(db, user.id, today=today)
    assert targets.calories == targets.base_calories == 2300
    assert targets.adaptive.status == "custom_override"
    assert targets.adaptive.applied is False


def test_health_summary_and_assistant_share_the_effective_target(monkeypatch):
    from backend.app import adaptive_targets
    from backend.app.adaptive_targets import refresh_adaptive_target
    from backend.app.assistant_service import _profile as assistant_profile
    from backend.app.health_service import build_health_summary

    today = date(2026, 8, 9)
    monkeypatch.setattr(adaptive_targets, "local_today", lambda timezone_name="UTC": today)
    db = _session()
    user, _ = _profile(db)
    _connect(db, user.id)
    _add_burns(db, user.id, today, range(1, 11), 3000)
    effective = refresh_adaptive_target(db, user.id, today=today)

    summary = build_health_summary(
        db,
        user.id,
        start_date=today - timedelta(days=1),
        end_date=today,
        timezone_name="UTC",
        locale="cs",
    )
    assistant = assistant_profile(db, user, "UTC")

    assert summary["targets"]["calories"] == effective.calories
    assert summary["targets"]["adaptive"]["status"] == "active"
    assert assistant["profile"]["target_calories"] == effective.calories
    assert assistant["profile"]["adaptive_calories"]["status"] == "active"


def test_existing_sqlite_profile_schema_gets_adaptive_columns(monkeypatch):
    from backend.app import database

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE user_profiles (id INTEGER PRIMARY KEY)"))

    monkeypatch.setattr(database, "engine", engine)
    database._ensure_profile_schema()

    columns = {column["name"] for column in inspect(engine).get_columns("user_profiles")}
    assert {
        "adaptive_calories_enabled",
        "adaptive_target_calories",
        "adaptive_target_updated_on",
    }.issubset(columns)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO user_profiles (id) VALUES (1)"))
        enabled = connection.execute(
            text("SELECT adaptive_calories_enabled FROM user_profiles WHERE id = 1")
        ).scalar_one()
    assert enabled in (False, 0)
