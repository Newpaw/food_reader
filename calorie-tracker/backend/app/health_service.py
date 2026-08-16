import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import models
from .adaptive_targets import resolve_nutrition_targets
from .oura_models import OuraDailyMetric
from .oura_service import parse_oura_details


def _safe_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 5:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    x_mean = mean(xs)
    y_mean = mean(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var <= 0 or y_var <= 0:
        return None
    return round(numerator / math.sqrt(x_var * y_var), 3)


def _correlation_label(value: float | None, *, locale: str) -> str:
    if value is None:
        return "málo dat" if locale == "cs" else "not enough data"
    strength = abs(value)
    if strength < 0.2:
        label = "velmi slabá" if locale == "cs" else "very weak"
    elif strength < 0.4:
        label = "slabá" if locale == "cs" else "weak"
    elif strength < 0.6:
        label = "střední" if locale == "cs" else "moderate"
    else:
        label = "silná" if locale == "cs" else "strong"
    direction = ("pozitivní" if value >= 0 else "negativní") if locale == "cs" else ("positive" if value >= 0 else "negative")
    return f"{label} {direction}"


def _day_range(start_date: date, end_date: date) -> list[date]:
    days = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def _aggregate_meals(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date,
    timezone_name: str,
) -> dict[str, dict]:
    tz = _safe_zoneinfo(timezone_name)
    start_local = datetime.combine(start_date, time.min, tzinfo=tz)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    meals = (
        db.query(models.Meal)
        .filter(
            models.Meal.user_id == user_id,
            models.Meal.consumed_at >= start_utc,
            models.Meal.consumed_at < end_utc,
        )
        .order_by(models.Meal.consumed_at.asc())
        .all()
    )

    totals: dict[str, dict] = defaultdict(
        lambda: {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "fiber_g": 0,
            "meal_count": 0,
            "last_meal_hour": None,
        }
    )
    for meal in meals:
        local_dt = meal.consumed_at.astimezone(tz)
        key = local_dt.date().isoformat()
        day = totals[key]
        day["calories"] += meal.calories or 0
        day["protein_g"] += meal.protein or 0
        day["carbs_g"] += meal.carbs or 0
        day["fat_g"] += meal.fat or 0
        day["fiber_g"] += meal.fiber or 0
        day["meal_count"] += 1
        day["last_meal_hour"] = round(local_dt.hour + local_dt.minute / 60, 2)
    return totals


def _oura_payload(oura: OuraDailyMetric) -> dict:
    """Compact but rich daily Oura context used by Health Coach and other AI."""

    return {
        "activity_score": oura.activity_score,
        "active_calories": oura.active_calories,
        "total_calories": oura.total_calories,
        "steps": oura.steps,
        "activity_target_calories": oura.activity_target_calories,
        "average_met_minutes": oura.average_met_minutes,
        "equivalent_walking_distance_m": oura.equivalent_walking_distance_m,
        "sedentary_seconds": oura.sedentary_seconds,
        "resting_seconds": oura.resting_seconds,
        "low_activity_seconds": oura.low_activity_seconds,
        "medium_activity_seconds": oura.medium_activity_seconds,
        "high_activity_seconds": oura.high_activity_seconds,
        "non_wear_seconds": oura.non_wear_seconds,
        "inactivity_alerts": oura.inactivity_alerts,
        "readiness_score": oura.readiness_score,
        "temperature_deviation_c": oura.temperature_deviation_c,
        "temperature_trend_deviation_c": oura.temperature_trend_deviation_c,
        "sleep_score": oura.sleep_score,
        "total_sleep_seconds": oura.total_sleep_seconds,
        "time_in_bed_seconds": oura.time_in_bed_seconds,
        "awake_seconds": oura.awake_seconds,
        "light_sleep_seconds": oura.light_sleep_seconds,
        "deep_sleep_seconds": oura.deep_sleep_seconds,
        "rem_sleep_seconds": oura.rem_sleep_seconds,
        "sleep_latency_seconds": oura.sleep_latency_seconds,
        "sleep_efficiency": oura.sleep_efficiency,
        "average_hrv_ms": oura.average_hrv_ms,
        "lowest_heart_rate_bpm": oura.lowest_heart_rate_bpm,
        "average_heart_rate_bpm": oura.average_heart_rate_bpm,
        "average_breaths_per_minute": oura.average_breaths_per_minute,
        "bedtime_start": oura.bedtime_start,
        "bedtime_end": oura.bedtime_end,
        "stress_high_seconds": oura.stress_high_seconds,
        "recovery_high_seconds": oura.recovery_high_seconds,
        "workout_count": oura.workout_count,
        "workout_calories": oura.workout_calories,
        "workout_seconds": oura.workout_seconds,
        "spo2_average_percent": oura.spo2_average_percent,
        "resilience_level": oura.resilience_level,
        "vascular_age_years": oura.vascular_age_years,
        "vo2_max": oura.vo2_max,
        "heart_rate_average_bpm": oura.heart_rate_average_bpm,
        "heart_rate_min_bpm": oura.heart_rate_min_bpm,
        "heart_rate_max_bpm": oura.heart_rate_max_bpm,
        "heart_rate_samples": oura.heart_rate_samples,
        "details": parse_oura_details(oura.details_json),
    }


def build_health_summary(
    db: Session,
    user_id: int,
    *,
    start_date: date,
    end_date: date,
    timezone_name: str,
    locale: str = "cs",
) -> dict:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    if (end_date - start_date).days > 365:
        raise ValueError("Health summary supports a maximum range of 366 days")

    meal_days = _aggregate_meals(db, user_id, start_date, end_date, timezone_name)
    metrics = (
        db.query(OuraDailyMetric)
        .filter(
            OuraDailyMetric.user_id == user_id,
            OuraDailyMetric.day >= start_date.isoformat(),
            OuraDailyMetric.day <= end_date.isoformat(),
        )
        .order_by(OuraDailyMetric.day.asc())
        .all()
    )
    metric_by_day = {metric.day: metric for metric in metrics}

    rows: list[dict] = []
    for day in _day_range(start_date, end_date):
        key = day.isoformat()
        nutrition = meal_days.get(key, {})
        oura = metric_by_day.get(key)
        intake = nutrition.get("calories", 0)
        expenditure = oura.total_calories if oura else None
        balance = intake - expenditure if expenditure is not None and nutrition.get("meal_count", 0) else None
        rows.append(
            {
                "day": key,
                "nutrition": {
                    "calories": intake,
                    "protein_g": nutrition.get("protein_g", 0),
                    "carbs_g": nutrition.get("carbs_g", 0),
                    "fat_g": nutrition.get("fat_g", 0),
                    "fiber_g": nutrition.get("fiber_g", 0),
                    "meal_count": nutrition.get("meal_count", 0),
                    "last_meal_hour": nutrition.get("last_meal_hour"),
                },
                "oura": None if oura is None else _oura_payload(oura),
                "energy_balance_kcal": balance,
            }
        )

    completed_balances = [row["energy_balance_kcal"] for row in rows if row["energy_balance_kcal"] is not None]
    readiness_values = [row["oura"]["readiness_score"] for row in rows if row["oura"] and row["oura"]["readiness_score"] is not None]
    sleep_values = [row["oura"]["sleep_score"] for row in rows if row["oura"] and row["oura"]["sleep_score"] is not None]

    next_day_readiness_pairs_calories: list[tuple[float, float]] = []
    next_day_readiness_pairs_protein: list[tuple[float, float]] = []
    next_day_readiness_pairs_balance: list[tuple[float, float]] = []
    late_sleep_scores: list[float] = []
    early_sleep_scores: list[float] = []

    for index, row in enumerate(rows[:-1]):
        next_row = rows[index + 1]
        readiness = next_row["oura"]["readiness_score"] if next_row["oura"] else None
        sleep_score = next_row["oura"]["sleep_score"] if next_row["oura"] else None
        nutrition = row["nutrition"]
        if nutrition["meal_count"] and readiness is not None:
            next_day_readiness_pairs_calories.append((nutrition["calories"], readiness))
            next_day_readiness_pairs_protein.append((nutrition["protein_g"], readiness))
            if row["energy_balance_kcal"] is not None:
                next_day_readiness_pairs_balance.append((row["energy_balance_kcal"], readiness))
        last_meal_hour = nutrition.get("last_meal_hour")
        if nutrition["meal_count"] and last_meal_hour is not None and sleep_score is not None:
            if last_meal_hour >= 21:
                late_sleep_scores.append(sleep_score)
            else:
                early_sleep_scores.append(sleep_score)

    calorie_readiness_corr = _pearson(next_day_readiness_pairs_calories)
    protein_readiness_corr = _pearson(next_day_readiness_pairs_protein)
    balance_readiness_corr = _pearson(next_day_readiness_pairs_balance)

    insights: list[dict[str, str]] = []
    if completed_balances:
        avg_balance = round(mean(completed_balances))
        if locale == "cs":
            direction = "deficit" if avg_balance < 0 else "nadbytek"
            detail = f"Průměrná energetická bilance v období je {avg_balance:+d} kcal/den ({direction}). Hodnoť hlavně trend, ne jednotlivý den."
            title = "Energetická bilance"
        else:
            direction = "deficit" if avg_balance < 0 else "surplus"
            detail = f"Average energy balance is {avg_balance:+d} kcal/day ({direction}). Use the trend, not a single day, for decisions."
            title = "Energy balance"
        insights.append({"kind": "energy_balance", "title": title, "detail": detail})

    if balance_readiness_corr is not None:
        label = _correlation_label(balance_readiness_corr, locale=locale)
        detail = (
            f"Vztah mezi energetickou bilancí a readiness následující den je {label} (r={balance_readiness_corr:+.2f}). Korelace není příčina."
            if locale == "cs"
            else f"Energy balance vs next-day readiness shows a {label} relationship (r={balance_readiness_corr:+.2f}). Correlation is not causation."
        )
        insights.append({"kind": "balance_readiness", "title": "Deficit vs. readiness" if locale == "cs" else "Balance vs readiness", "detail": detail})

    if protein_readiness_corr is not None:
        label = _correlation_label(protein_readiness_corr, locale=locale)
        detail = (
            f"Protein proti readiness následující den: {label} vztah (r={protein_readiness_corr:+.2f})."
            if locale == "cs"
            else f"Protein vs next-day readiness: {label} relationship (r={protein_readiness_corr:+.2f})."
        )
        insights.append({"kind": "protein_readiness", "title": "Protein a regenerace" if locale == "cs" else "Protein and recovery", "detail": detail})

    if len(late_sleep_scores) >= 3 and len(early_sleep_scores) >= 3:
        late_avg = round(mean(late_sleep_scores), 1)
        early_avg = round(mean(early_sleep_scores), 1)
        diff = round(late_avg - early_avg, 1)
        detail = (
            f"Po posledním jídle po 21:00 máš průměrné sleep score {late_avg}; při dřívějším posledním jídle {early_avg}. Rozdíl {diff:+.1f} bodu."
            if locale == "cs"
            else f"After last meals at or after 21:00, average sleep score is {late_avg}; after earlier last meals it is {early_avg}. Difference {diff:+.1f} points."
        )
        insights.append({"kind": "late_meal_sleep", "title": "Čas posledního jídla" if locale == "cs" else "Last meal timing", "detail": detail})

    if len(insights) < 2:
        insights.append(
            {
                "kind": "data_quality",
                "title": "Potřebujeme víc dat" if locale == "cs" else "More data needed",
                "detail": (
                    "Pro smysluplné osobní korelace loguj jídlo a synchronizuj Ouru alespoň 2–3 týdny."
                    if locale == "cs"
                    else "For useful personal correlations, log meals and sync Oura consistently for at least 2–3 weeks."
                ),
            }
        )

    latest_weight = (
        db.query(models.WithingsMeasurement)
        .filter(models.WithingsMeasurement.user_id == user_id, models.WithingsMeasurement.weight_kg.isnot(None))
        .order_by(models.WithingsMeasurement.measured_at.desc())
        .first()
    )

    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    resolved_targets = resolve_nutrition_targets(db, user_id, timezone_name=timezone_name)
    targets = None
    if profile is not None and resolved_targets is not None:
        targets = {
            "calories": resolved_targets.calories,
            "base_calories": resolved_targets.base_calories,
            "protein_g": resolved_targets.protein_g,
            "carbs_g": resolved_targets.carbs_g,
            "fat_g": resolved_targets.fats_g,
            "fiber_g": resolved_targets.fiber_g,
            "goal": profile.goal,
            "dietary_preference": profile.dietary_preference,
            "adaptive": resolved_targets.adaptive.model_dump(),
        }

    return {
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "timezone": timezone_name,
        "targets": targets,
        "days": rows,
        "summary": {
            "days_with_food": sum(1 for row in rows if row["nutrition"]["meal_count"] > 0),
            "days_with_oura": sum(1 for row in rows if row["oura"] is not None),
            "average_energy_balance_kcal": round(mean(completed_balances)) if completed_balances else None,
            "average_readiness": round(mean(readiness_values), 1) if readiness_values else None,
            "average_sleep_score": round(mean(sleep_values), 1) if sleep_values else None,
            "latest_weight_kg": latest_weight.weight_kg if latest_weight else None,
            "correlations": {
                "calories_to_next_day_readiness": calorie_readiness_corr,
                "protein_to_next_day_readiness": protein_readiness_corr,
                "energy_balance_to_next_day_readiness": balance_readiness_corr,
            },
        },
        "insights": insights,
    }
