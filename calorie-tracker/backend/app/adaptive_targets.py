from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import models, schemas
from .nutrition_calculator import NutritionCalculator
from .oura_models import OuraConnection, OuraDailyMetric


LOOKBACK_DAYS = 14
MIN_DATA_DAYS = 10
MAX_DATA_AGE_DAYS = 2
PROFILE_WEIGHT = 0.70
WEARABLE_WEIGHT = 0.30
MAX_TOTAL_ADJUSTMENT_KCAL = 250
MAX_DAILY_CHANGE_KCAL = 100
RECOMMENDED_RANGE_KCAL = 100


def local_today(timezone_name: str = "UTC") -> date:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = timezone.utc
    return datetime.now(zone).date()


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _oura_burn_snapshot(db: Session, user_id: int, today: date) -> tuple[int, int | None, date | None]:
    first_day = today - timedelta(days=LOOKBACK_DAYS)
    last_day = today - timedelta(days=1)
    rows = (
        db.query(OuraDailyMetric)
        .filter(
            OuraDailyMetric.user_id == user_id,
            OuraDailyMetric.day >= first_day.isoformat(),
            OuraDailyMetric.day <= last_day.isoformat(),
            OuraDailyMetric.total_calories.is_not(None),
            OuraDailyMetric.total_calories > 0,
        )
        .order_by(OuraDailyMetric.day.asc())
        .all()
    )
    burns = [int(row.total_calories) for row in rows]
    latest_day = date.fromisoformat(rows[-1].day) if rows else None
    burn_baseline = round(median(burns)) if burns else None
    return len(burns), burn_baseline, latest_day


def _adaptive_state(
    db: Session,
    profile: models.UserProfile,
    *,
    today: date,
    persist: bool,
) -> tuple[schemas.AdaptiveCaloriesOut, int]:
    base_calories = int(profile.target_calories)
    enabled = bool(profile.adaptive_calories_enabled)

    if not enabled:
        return schemas.AdaptiveCaloriesOut(enabled=False, applied=False, status="disabled"), base_calories

    if profile.custom_calories is not None:
        return schemas.AdaptiveCaloriesOut(enabled=True, applied=False, status="custom_override"), base_calories

    connection = db.query(OuraConnection).filter(OuraConnection.user_id == profile.user_id).first()
    if connection is None:
        return schemas.AdaptiveCaloriesOut(enabled=True, applied=False, status="not_connected"), base_calories

    data_days, burn_baseline, latest_day = _oura_burn_snapshot(db, profile.user_id, today)
    common = {
        "enabled": True,
        "applied": False,
        "source": "oura",
        "data_days": data_days,
        "burn_baseline": burn_baseline,
    }
    if data_days < MIN_DATA_DAYS or burn_baseline is None:
        return schemas.AdaptiveCaloriesOut(status="warming_up", **common), base_calories

    if latest_day is None or (today - latest_day).days > MAX_DATA_AGE_DAYS:
        return schemas.AdaptiveCaloriesOut(status="stale", **common), base_calories

    goal_adjustment = NutritionCalculator.GOAL_ADJUSTMENTS.get(profile.goal or "maintenance", 0)
    adaptive_tdee = PROFILE_WEIGHT * float(profile.tdee) + WEARABLE_WEIGHT * burn_baseline
    raw_target = round(adaptive_tdee + goal_adjustment)
    bounded_target = _clamp(
        raw_target,
        base_calories - MAX_TOTAL_ADJUSTMENT_KCAL,
        base_calories + MAX_TOTAL_ADJUSTMENT_KCAL,
    )

    previous_target = profile.adaptive_target_calories
    previous_day = profile.adaptive_target_updated_on
    if previous_target is None or previous_day is None:
        anchor = base_calories
        allowance = MAX_DAILY_CHANGE_KCAL
    else:
        anchor = _clamp(
            int(previous_target),
            base_calories - MAX_TOTAL_ADJUSTMENT_KCAL,
            base_calories + MAX_TOTAL_ADJUSTMENT_KCAL,
        )
        elapsed_days = max(0, (today - previous_day).days)
        allowance = elapsed_days * MAX_DAILY_CHANGE_KCAL

    effective_target = anchor + _clamp(bounded_target - anchor, -allowance, allowance)
    effective_target = _clamp(
        effective_target,
        base_calories - MAX_TOTAL_ADJUSTMENT_KCAL,
        base_calories + MAX_TOTAL_ADJUSTMENT_KCAL,
    )

    if persist:
        profile.adaptive_target_calories = effective_target
        profile.adaptive_target_updated_on = today
        profile.updated_at = datetime.now(timezone.utc)

    adaptive = schemas.AdaptiveCaloriesOut(
        enabled=True,
        applied=True,
        status="active",
        source="oura",
        data_days=data_days,
        burn_baseline=burn_baseline,
        adjustment_kcal=effective_target - base_calories,
        recommended_min_calories=max(0, effective_target - RECOMMENDED_RANGE_KCAL),
        recommended_max_calories=effective_target + RECOMMENDED_RANGE_KCAL,
    )
    return adaptive, effective_target


def _effective_macros(profile: models.UserProfile, effective_calories: int) -> tuple[int, int, int, int]:
    protein = int(profile.target_protein_g)
    carbs = int(profile.target_carbs_g)
    fats = int(profile.target_fats_g)
    fiber = int(profile.target_fiber_g)
    calorie_delta = effective_calories - int(profile.target_calories)

    adjustable_carbs = profile.custom_carbs_g is None
    adjustable_fats = profile.custom_fats_g is None
    if calorie_delta and adjustable_carbs and adjustable_fats:
        carb_energy = max(0, carbs * 4)
        fat_energy = max(0, fats * 9)
        non_protein_energy = carb_energy + fat_energy
        carb_share = carb_energy / non_protein_energy if non_protein_energy else 0.5
        carbs = max(0, carbs + round((calorie_delta * carb_share) / 4))
        fats = max(0, fats + round((calorie_delta * (1 - carb_share)) / 9))
    elif calorie_delta and adjustable_carbs:
        carbs = max(0, carbs + round(calorie_delta / 4))
    elif calorie_delta and adjustable_fats:
        fats = max(0, fats + round(calorie_delta / 9))

    return protein, carbs, fats, fiber


def resolve_nutrition_targets(
    db: Session,
    user_id: int,
    *,
    timezone_name: str = "UTC",
    today: date | None = None,
    persist: bool = False,
) -> schemas.NutritionTargets | None:
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if not profile or not profile.target_calories:
        return None

    current_day = today or local_today(timezone_name)
    adaptive, effective_calories = _adaptive_state(db, profile, today=current_day, persist=persist)

    if not adaptive.applied and persist:
        profile.adaptive_target_calories = None
        profile.adaptive_target_updated_on = None

    protein, carbs, fats, fiber = _effective_macros(profile, effective_calories)
    if profile.custom_calories is not None:
        method = "Custom values provided by user"
        method_code = "custom"
    elif adaptive.applied:
        method = "Calculated using Mifflin-St Jeor equation and a 14-day Oura expenditure baseline"
        method_code = "adaptive"
    else:
        method = f"Calculated using Mifflin-St Jeor equation (BMR: {profile.bmr:.0f} cal, TDEE: {profile.tdee:.0f} cal)"
        method_code = "profile"

    return schemas.NutritionTargets(
        calories=effective_calories,
        base_calories=int(profile.target_calories),
        protein_g=protein,
        carbs_g=carbs,
        fats_g=fats,
        fiber_g=fiber,
        calculation_method=method,
        calculation_method_code=method_code,
        bmr=profile.bmr,
        tdee=profile.tdee,
        last_updated=profile.updated_at,
        adaptive=adaptive,
    )


def refresh_adaptive_target(
    db: Session,
    user_id: int,
    *,
    timezone_name: str = "UTC",
    today: date | None = None,
) -> schemas.NutritionTargets | None:
    targets = resolve_nutrition_targets(
        db,
        user_id,
        timezone_name=timezone_name,
        today=today,
        persist=True,
    )
    db.commit()
    return targets
