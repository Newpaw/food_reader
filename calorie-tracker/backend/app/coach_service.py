from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import models, schemas
from .nutrition_calculator import NutritionCalculator


DISCLAIMER = (
    "This is general nutrition coaching, not medical advice. If you have a medical condition, "
    "a history of disordered eating, or unusual symptoms, use a qualified clinician."
)


def resolve_timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Europe/Prague")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local_day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _percent(current: int, target: int | None) -> int | None:
    if not target or target <= 0:
        return None
    return max(0, round(current / target * 100))


def _metric(current: int, target: int | None) -> schemas.CoachMetric:
    return schemas.CoachMetric(
        current=current,
        target=target,
        remaining=None if target is None else target - current,
        percentage=_percent(current, target),
    )


def _meal_totals(meals: list[models.Meal]) -> dict[str, int]:
    return {
        "calories": sum(int(meal.calories or 0) for meal in meals),
        "protein": sum(int(meal.protein or 0) for meal in meals),
        "fiber": sum(int(meal.fiber or 0) for meal in meals),
        "meals": len(meals),
    }


def _checkin_schema(row: models.DailyCheckin | None) -> schemas.DailyCheckinOut | None:
    if row is None:
        return None
    return schemas.DailyCheckinOut(
        date=date.fromisoformat(row.checkin_date),
        hunger=row.hunger,
        energy=row.energy,
        sleep_hours=row.sleep_hours,
        steps=row.steps,
        trained=bool(row.trained),
        note=row.note,
    )


def get_daily_checkin(db: Session, user_id: int, day: date) -> models.DailyCheckin | None:
    return (
        db.query(models.DailyCheckin)
        .filter(models.DailyCheckin.user_id == user_id, models.DailyCheckin.checkin_date == day.isoformat())
        .first()
    )


def save_daily_checkin(
    db: Session,
    user_id: int,
    payload: schemas.DailyCheckinIn,
) -> schemas.DailyCheckinOut:
    tz = resolve_timezone(payload.timezone)
    today = datetime.now(tz).date()
    row = get_daily_checkin(db, user_id, today)
    if row is None:
        row = models.DailyCheckin(user_id=user_id, checkin_date=today.isoformat())
        db.add(row)
    update = payload.model_dump(exclude={"timezone"}, exclude_unset=True)
    for key, value in update.items():
        if key == "note" and value:
            value = " ".join(str(value).replace("<", "‹").replace(">", "›").split())[:500]
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _checkin_schema(row)


def _calorie_adherence(calories: int, target: int | None) -> float:
    if not target or target <= 0:
        return 0.0
    deviation = abs(calories - target) / target
    if deviation <= 0.05:
        return 1.0
    if deviation >= 0.40:
        return 0.0
    return max(0.0, 1.0 - (deviation - 0.05) / 0.35)


def _daily_score(totals: dict[str, int], profile: models.UserProfile | None) -> int:
    if not profile or not profile.target_calories:
        return 0
    protein = min(totals["protein"] / max(profile.target_protein_g or 1, 1), 1.0)
    fiber = min(totals["fiber"] / max(profile.target_fiber_g or 1, 1), 1.0)
    completeness = min(totals["meals"] / 3, 1.0)
    return round((_calorie_adherence(totals["calories"], profile.target_calories) * 0.45 + protein * 0.30 + fiber * 0.15 + completeness * 0.10) * 100)


def _protein_foods(preference: str | None) -> list[str]:
    if preference == "vegan":
        return ["tofu or tempeh", "lentils", "soy yogurt", "seitan"]
    if preference == "vegetarian":
        return ["skyr or Greek yogurt", "eggs", "cottage cheese", "tofu"]
    return ["chicken or turkey", "tuna", "skyr", "cottage cheese"]


def _next_action(
    totals: dict[str, int],
    profile: models.UserProfile | None,
    local_hour: int,
    checkin: models.DailyCheckin | None,
) -> schemas.CoachAction:
    if not profile or not profile.target_calories:
        return schemas.CoachAction(
            title="Complete your weight-loss profile",
            body="Set current weight, height, age, activity and goal. Add a target weight so progress can be measured against a concrete destination.",
            priority="high",
            action_type="complete_profile",
        )
    if profile.goal != "weight_loss":
        return schemas.CoachAction(
            title="Switch the profile goal to weight loss",
            body="Your current profile is not configured for fat loss, so the calorie and trend recommendations cannot adapt correctly.",
            priority="high",
            action_type="set_weight_loss_goal",
        )

    calorie_gap = profile.target_calories - totals["calories"]
    protein_gap = int(profile.target_protein_g or 0) - totals["protein"]
    fiber_gap = int(profile.target_fiber_g or 0) - totals["fiber"]

    if totals["meals"] == 0 and local_hour >= 10:
        return schemas.CoachAction(
            title="Log the first meal now",
            body="A complete log is more valuable than a perfect estimate. Add the meal, then correct portion size, oil, sauces and drinks if needed.",
            priority="high",
            action_type="log_meal",
        )
    if checkin and checkin.hunger and checkin.hunger >= 4 and fiber_gap > 6:
        return schemas.CoachAction(
            title="Reduce hunger with volume, not willpower",
            body="Hunger is high today. Keep the calorie target, but make the next meal larger through vegetables, fruit, legumes and lean protein.",
            priority="high",
            action_type="manage_hunger",
            suggested_foods=["large vegetable portion", "potatoes", "fruit", *_protein_foods(profile.dietary_preference)[:2]],
        )
    if calorie_gap < -150:
        return schemas.CoachAction(
            title="Protect the rest of the day",
            body=f"You are about {abs(calorie_gap)} kcal above target. Do not compensate by starving. Choose a light protein-focused next meal and return to the normal target tomorrow.",
            priority="high",
            action_type="limit_remaining_calories",
            suggested_foods=_protein_foods(profile.dietary_preference)[:3],
        )
    if protein_gap > 35 and calorie_gap > 250:
        return schemas.CoachAction(
            title="Make the next meal protein-first",
            body=f"You still need roughly {protein_gap} g protein. Build the next meal around a lean protein source before adding sides.",
            priority="high",
            action_type="increase_protein",
            suggested_foods=_protein_foods(profile.dietary_preference),
        )
    if fiber_gap > 10 and calorie_gap > 150:
        return schemas.CoachAction(
            title="Add volume and fiber",
            body=f"You are about {fiber_gap} g short on fiber. Add vegetables, fruit, legumes or a whole-grain side.",
            priority="medium",
            action_type="increase_fiber",
            suggested_foods=["large vegetable portion", "berries or apple", "beans or lentils", "whole-grain side"],
        )
    if calorie_gap > 500 and local_hour >= 19:
        return schemas.CoachAction(
            title="Check whether the log is complete",
            body=f"The diary still shows {calorie_gap} kcal remaining late in the day. Add missing drinks, sauces, snacks and tasting portions before treating this as a real deficit.",
            priority="medium",
            action_type="complete_log",
        )
    return schemas.CoachAction(
        title="Stay on the plan",
        body=f"You have about {max(calorie_gap, 0)} kcal remaining. Keep the next choice simple, protein-led and stop when comfortably satisfied.",
        priority="low",
        action_type="maintain",
    )


def build_today(db: Session, user_id: int, tz_name: str | None = None) -> schemas.CoachTodayOut:
    tz = resolve_timezone(tz_name)
    now_local = datetime.now(tz)
    start_utc, end_utc = local_day_bounds(now_local.date(), tz)
    meals = (
        db.query(models.Meal)
        .filter(models.Meal.user_id == user_id, models.Meal.consumed_at >= start_utc, models.Meal.consumed_at < end_utc)
        .order_by(models.Meal.consumed_at.asc())
        .all()
    )
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    checkin = get_daily_checkin(db, user_id, now_local.date())
    totals = _meal_totals(meals)
    warnings: list[str] = []
    if meals and any((meal.confidence or 100) < 45 for meal in meals):
        warnings.append("At least one meal has a low-confidence estimate. Review portion size, oil, sauces and drinks.")
    if now_local.hour >= 20 and totals["meals"] < 2:
        warnings.append("Today may be incompletely logged; low intake is not reliable until missing meals and snacks are added.")
    if checkin and checkin.sleep_hours is not None and checkin.sleep_hours < 6:
        warnings.append("Sleep was short. Expect more hunger and avoid making the calorie target more aggressive today.")
    if checkin and checkin.energy is not None and checkin.energy <= 2:
        warnings.append("Energy is low. Prioritize recovery, protein and normal calories rather than adding extra restriction.")

    return schemas.CoachTodayOut(
        date=now_local.date(),
        goal=profile.goal if profile and profile.goal else "weight_loss",
        calories=_metric(totals["calories"], profile.target_calories if profile else None),
        protein=_metric(totals["protein"], profile.target_protein_g if profile else None),
        fiber=_metric(totals["fiber"], profile.target_fiber_g if profile else None),
        meals_logged=totals["meals"],
        logging_complete=totals["meals"] >= 3 or (now_local.hour < 14 and totals["meals"] >= 1),
        adherence_score=_daily_score(totals, profile),
        next_action=_next_action(totals, profile, now_local.hour, checkin),
        warnings=warnings,
        checkin=_checkin_schema(checkin),
        disclaimer=DISCLAIMER,
    )


def _linear_weight_trend(measurements: list[models.WithingsMeasurement]) -> schemas.WeightTrendOut:
    usable = [item for item in measurements if item.weight_kg is not None]
    if not usable:
        return schemas.WeightTrendOut(measurements=0, direction="unknown")
    usable.sort(key=lambda item: item.measured_at)
    latest = float(usable[-1].weight_kg)
    if len(usable) == 1:
        return schemas.WeightTrendOut(measurements=1, latest_weight_kg=round(latest, 2), direction="unknown")
    first_time = usable[0].measured_at
    xs = [(item.measured_at - first_time).total_seconds() / 86400 for item in usable]
    ys = [float(item.weight_kg) for item in usable]
    x_bar, y_bar = mean(xs), mean(ys)
    denominator = sum((x - x_bar) ** 2 for x in xs)
    slope = 0.0 if denominator == 0 else sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / denominator
    weekly = slope * 7
    weekly_percent = weekly / y_bar * 100 if y_bar else 0.0
    direction = "stable" if abs(weekly) <= 0.1 else "down" if weekly < 0 else "up"
    return schemas.WeightTrendOut(
        measurements=len(usable),
        latest_weight_kg=round(latest, 2),
        change_kg=round(latest - float(usable[0].weight_kg), 2),
        weekly_change_kg=round(weekly, 2),
        weekly_change_percent=round(weekly_percent, 2),
        direction=direction,
    )


def _adaptive_target(
    profile: models.UserProfile | None,
    trend: schemas.WeightTrendOut,
    completeness: int,
    average_logged_calories: int,
) -> schemas.AdaptiveTargetOut:
    target = profile.target_calories if profile else None
    if not profile or profile.goal != "weight_loss" or not target:
        return schemas.AdaptiveTargetOut(current_target=target, recommended_target=target, reason="Adaptive calorie changes require a configured weight-loss goal.", eligible=False)
    if trend.measurements < 4 or trend.weekly_change_percent is None or completeness < 70:
        return schemas.AdaptiveTargetOut(
            current_target=target,
            recommended_target=target,
            reason="Keep the current target until there are at least four weight readings and at least 70% logging completeness.",
            eligible=False,
        )

    desired = float(profile.desired_weekly_loss_percent or 0.6)
    slow_threshold = max(0.2, desired - 0.25)
    fast_threshold = min(1.0, desired + 0.25)
    loss_rate = -float(trend.weekly_change_percent)
    adjustment = 0
    reason = f"Weight trend is close to the selected {desired:.1f}% weekly pace; keep the current target."
    if loss_rate < slow_threshold and average_logged_calories <= target * 1.08:
        adjustment = -100
        reason = "Weight is falling more slowly than the selected pace despite reasonable calorie adherence. Test a small 100 kcal reduction for two weeks."
    elif loss_rate > fast_threshold:
        adjustment = 100
        reason = "Weight is falling faster than the selected pace. Add 100 kcal to protect recovery, training and adherence."

    floor = max(1200, round((profile.bmr or 1200) * 1.05))
    recommended = max(floor, target + adjustment)
    actual = recommended - target
    return schemas.AdaptiveTargetOut(
        current_target=target,
        recommended_target=recommended,
        adjustment=actual,
        reason=reason if actual == adjustment else "The recommendation was limited by the app's minimum calorie guardrail.",
        eligible=True,
    )


def build_weekly(db: Session, user_id: int, tz_name: str | None = None, days: int = 7) -> schemas.CoachWeeklyOut:
    days = min(max(days, 7), 28)
    tz = resolve_timezone(tz_name)
    today = datetime.now(tz).date()
    start_day = today - timedelta(days=days - 1)
    start_utc, _ = local_day_bounds(start_day, tz)
    _, end_utc = local_day_bounds(today, tz)
    meals = db.query(models.Meal).filter(models.Meal.user_id == user_id, models.Meal.consumed_at >= start_utc, models.Meal.consumed_at < end_utc).all()
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()

    grouped: dict[date, list[models.Meal]] = defaultdict(list)
    for meal in meals:
        grouped[meal.consumed_at.astimezone(tz).date()].append(meal)
    all_days = [start_day + timedelta(days=index) for index in range(days)]
    daily_totals = [_meal_totals(grouped[day]) for day in all_days]
    logged = [total for total in daily_totals if total["meals"] > 0]
    logged_days = len(logged)
    completeness = round(logged_days / days * 100)
    total_calories = sum(item["calories"] for item in daily_totals)
    avg_all = round(total_calories / days)
    avg_logged = round(total_calories / logged_days) if logged_days else 0
    avg_protein = round(sum(item["protein"] for item in daily_totals) / days)
    avg_fiber = round(sum(item["fiber"] for item in daily_totals) / days)
    target = profile.target_calories if profile else None
    days_on_target = sum(1 for total in daily_totals if target and total["meals"] > 0 and abs(total["calories"] - target) <= target * 0.10)

    checkins = db.query(models.DailyCheckin).filter(models.DailyCheckin.user_id == user_id, models.DailyCheckin.checkin_date >= start_day.isoformat(), models.DailyCheckin.checkin_date <= today.isoformat()).all()
    hunger_values = [row.hunger for row in checkins if row.hunger is not None]
    energy_values = [row.energy for row in checkins if row.energy is not None]
    training_days = sum(1 for row in checkins if row.trained)

    weight_start = datetime.now(timezone.utc) - timedelta(days=max(days * 2, 14))
    measurements = (
        db.query(models.WithingsMeasurement)
        .filter(models.WithingsMeasurement.user_id == user_id, models.WithingsMeasurement.weight_kg.isnot(None), models.WithingsMeasurement.measured_at >= weight_start)
        .order_by(models.WithingsMeasurement.measured_at.asc())
        .all()
    )
    trend = _linear_weight_trend(measurements)
    adaptive = _adaptive_target(profile, trend, completeness, avg_logged)

    wins: list[str] = []
    focus: list[str] = []
    if completeness >= 85:
        wins.append("Logging was consistent enough to trust the weekly pattern.")
    else:
        focus.append("Log every day, including alcohol, sauces, snacks and small tasting portions.")
    if profile and profile.target_protein_g and avg_protein >= profile.target_protein_g * 0.9:
        wins.append("Average protein intake was close to target.")
    else:
        focus.append("Plan a protein anchor for breakfast, lunch and dinner.")
    if profile and profile.target_fiber_g and avg_fiber >= profile.target_fiber_g * 0.8:
        wins.append("Fiber intake supported satiety on most days.")
    else:
        focus.append("Add one high-volume vegetable or fruit serving to two meals each day.")
    if trend.direction == "down":
        wins.append("The measured weight trend is moving down.")
    elif trend.direction == "up":
        focus.append("Review weekend intake, drinks and unlogged extras before cutting calories further.")
    if hunger_values and mean(hunger_values) >= 4:
        focus.append("Average hunger was high. Increase food volume and distribute protein more evenly before lowering calories.")
    if not wins:
        wins.append("You collected enough data to identify the next useful change.")

    estimated_weeks = None
    if profile and profile.target_weight_kg and trend.latest_weight_kg and trend.latest_weight_kg > profile.target_weight_kg:
        weekly_loss = abs(trend.weekly_change_kg or 0)
        if weekly_loss >= 0.1:
            estimated_weeks = max(1, round((trend.latest_weight_kg - profile.target_weight_kg) / weekly_loss))

    return schemas.CoachWeeklyOut(
        from_date=start_day,
        to_date=today,
        logged_days=logged_days,
        total_days=days,
        logging_completeness_percent=completeness,
        average_calories_all_days=avg_all,
        average_calories_logged_days=avg_logged,
        average_protein_g=avg_protein,
        average_fiber_g=avg_fiber,
        calorie_target=target,
        days_on_target=days_on_target,
        weight_trend=trend,
        adaptive_target=adaptive,
        wins=wins[:4],
        focus_next_week=focus[:4],
        average_hunger=round(mean(hunger_values), 1) if hunger_values else None,
        average_energy=round(mean(energy_values), 1) if energy_values else None,
        training_days=training_days,
        estimated_weeks_to_goal=estimated_weeks,
    )


def apply_adaptive_target(db: Session, user_id: int, tz_name: str | None = None) -> models.UserProfile:
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if profile is None:
        raise ValueError("Profile not found.")
    recommendation = build_weekly(db, user_id, tz_name).adaptive_target
    if not recommendation.eligible or recommendation.recommended_target is None:
        raise ValueError(recommendation.reason)
    target = recommendation.recommended_target
    protein, carbs, fats = NutritionCalculator.calculate_macros(target, profile.dietary_preference or "none", weight_kg=profile.weight_kg, goal=profile.goal or "weight_loss")
    profile.custom_calories = target
    profile.target_calories = target
    profile.target_protein_g = profile.custom_protein_g or protein
    profile.target_carbs_g = profile.custom_carbs_g or carbs
    profile.target_fats_g = profile.custom_fats_g or fats
    db.commit()
    db.refresh(profile)
    return profile


def coach_context(db: Session, user_id: int, tz_name: str | None = None) -> dict:
    today = build_today(db, user_id, tz_name)
    weekly = build_weekly(db, user_id, tz_name)
    actions = [today.next_action.body]
    if weekly.focus_next_week:
        actions.append(weekly.focus_next_week[0])
    grounded = [
        f"today calories {today.calories.current}/{today.calories.target or 'unknown'}",
        f"today protein {today.protein.current}/{today.protein.target or 'unknown'} g",
        f"logging completeness {weekly.logging_completeness_percent}%",
        f"weight trend {weekly.weight_trend.weekly_change_percent if weekly.weight_trend.weekly_change_percent is not None else 'unknown'}% per week",
    ]
    return {
        "today": today.model_dump(mode="json"),
        "weekly": weekly.model_dump(mode="json"),
        "fallback_answer": today.next_action.body,
        "fallback_actions": actions,
        "grounded_in": grounded,
    }
