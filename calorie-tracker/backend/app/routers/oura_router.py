import json
from datetime import date, datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..deps import get_current_user, get_db
from ..health_coach import generate_health_coach
from ..health_service import build_health_summary
from ..oura_models import OuraConnection, OuraDailyMetric
from ..oura_service import (
    OuraAPIError,
    OuraConfigError,
    build_authorization_url,
    decode_oauth_state,
    missing_oura_scopes,
    oura_configured,
    parse_oura_details,
    save_connection_from_code,
    sync_oura_data,
)
from ..settings import settings


router = APIRouter(prefix="/oura", tags=["oura"])


def _frontend_redirect(**params: str) -> RedirectResponse:
    separator = "&" if "?" in settings.OURA_FRONTEND_URL else "?"
    return RedirectResponse(f"{settings.OURA_FRONTEND_URL}{separator}{urlencode(params)}")


def _build_summary(
    db: Session,
    user_id: int,
    *,
    start_date: date,
    end_date: date,
    timezone_name: str,
    locale: str,
):
    try:
        return build_health_summary(
            db,
            user_id,
            start_date=start_date,
            end_date=end_date,
            timezone_name=timezone_name,
            locale=locale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _now_for_timezone(timezone_name: str) -> str:
    try:
        return datetime.now(ZoneInfo(timezone_name)).isoformat(timespec="minutes")
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now().astimezone().isoformat(timespec="minutes")


def _metric_payload(row: OuraDailyMetric) -> dict:
    return {
        "day": row.day,
        "activity_score": row.activity_score,
        "active_calories": row.active_calories,
        "total_calories": row.total_calories,
        "steps": row.steps,
        "activity_target_calories": row.activity_target_calories,
        "average_met_minutes": row.average_met_minutes,
        "equivalent_walking_distance_m": row.equivalent_walking_distance_m,
        "sedentary_seconds": row.sedentary_seconds,
        "resting_seconds": row.resting_seconds,
        "low_activity_seconds": row.low_activity_seconds,
        "medium_activity_seconds": row.medium_activity_seconds,
        "high_activity_seconds": row.high_activity_seconds,
        "non_wear_seconds": row.non_wear_seconds,
        "inactivity_alerts": row.inactivity_alerts,
        "activity_target_meters": row.activity_target_meters,
        "activity_meters_to_target": row.activity_meters_to_target,
        "readiness_score": row.readiness_score,
        "temperature_deviation_c": row.temperature_deviation_c,
        "temperature_trend_deviation_c": row.temperature_trend_deviation_c,
        "sleep_score": row.sleep_score,
        "total_sleep_seconds": row.total_sleep_seconds,
        "time_in_bed_seconds": row.time_in_bed_seconds,
        "awake_seconds": row.awake_seconds,
        "light_sleep_seconds": row.light_sleep_seconds,
        "deep_sleep_seconds": row.deep_sleep_seconds,
        "rem_sleep_seconds": row.rem_sleep_seconds,
        "sleep_latency_seconds": row.sleep_latency_seconds,
        "sleep_efficiency": row.sleep_efficiency,
        "average_hrv_ms": row.average_hrv_ms,
        "lowest_heart_rate_bpm": row.lowest_heart_rate_bpm,
        "average_heart_rate_bpm": row.average_heart_rate_bpm,
        "average_breaths_per_minute": row.average_breaths_per_minute,
        "bedtime_start": row.bedtime_start,
        "bedtime_end": row.bedtime_end,
        "sleep_score_delta": row.sleep_score_delta,
        "readiness_score_delta": row.readiness_score_delta,
        "low_battery_alert": row.low_battery_alert,
        "stress_high_seconds": row.stress_high_seconds,
        "recovery_high_seconds": row.recovery_high_seconds,
        "workout_count": row.workout_count,
        "workout_calories": row.workout_calories,
        "workout_seconds": row.workout_seconds,
        "spo2_average_percent": row.spo2_average_percent,
        "breathing_disturbance_index": row.breathing_disturbance_index,
        "resilience_level": row.resilience_level,
        "vascular_age_years": row.vascular_age_years,
        "pulse_wave_velocity_m_s": row.pulse_wave_velocity_m_s,
        "vo2_max": row.vo2_max,
        "heart_rate_average_bpm": row.heart_rate_average_bpm,
        "heart_rate_min_bpm": row.heart_rate_min_bpm,
        "heart_rate_max_bpm": row.heart_rate_max_bpm,
        "heart_rate_samples": row.heart_rate_samples,
        "rest_mode": row.rest_mode,
        "sleep_time_recommendation": row.sleep_time_recommendation,
        "sleep_time_status": row.sleep_time_status,
        "optimal_bedtime_start_offset_seconds": row.optimal_bedtime_start_offset_seconds,
        "optimal_bedtime_end_offset_seconds": row.optimal_bedtime_end_offset_seconds,
        "optimal_bedtime_timezone_offset_seconds": row.optimal_bedtime_timezone_offset_seconds,
        "details": parse_oura_details(row.details_json),
    }


def _ring_configurations(connection: OuraConnection | None) -> list[dict]:
    if connection is None or not connection.ring_configuration_json:
        return []
    try:
        value = json.loads(connection.ring_configuration_json)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


@router.get("/status")
def get_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = db.query(OuraConnection).filter(OuraConnection.user_id == current_user.id).first()
    metric_count = db.query(OuraDailyMetric).filter(OuraDailyMetric.user_id == current_user.id).count()
    latest = (
        db.query(OuraDailyMetric)
        .filter(OuraDailyMetric.user_id == current_user.id)
        .order_by(OuraDailyMetric.day.desc())
        .first()
    )
    missing_scopes = missing_oura_scopes(connection) if connection else []
    return {
        "configured": oura_configured(),
        "connected": connection is not None,
        "scope": connection.scope if connection else None,
        "missing_scopes": missing_scopes,
        "needs_reauthorization": bool(connection and missing_scopes),
        "last_sync_at": connection.last_sync_at if connection else None,
        "synced_days": metric_count,
        "latest_day": latest.day if latest else None,
        "latest_readiness": latest.readiness_score if latest else None,
        "latest_sleep_score": latest.sleep_score if latest else None,
        "latest_spo2": latest.spo2_average_percent if latest else None,
        "latest_resilience": latest.resilience_level if latest else None,
        "profile": (
            {
                "age": connection.profile_age,
                "weight_kg": connection.profile_weight_kg,
                "height_m": connection.profile_height_m,
                "biological_sex": connection.profile_biological_sex,
            }
            if connection
            else None
        ),
        "rings": _ring_configurations(connection),
        "ring_battery": (
            {
                "level_percent": connection.ring_battery_level_percent,
                "charging": connection.ring_battery_charging,
                "in_charger": connection.ring_battery_in_charger,
                "updated_at": connection.ring_battery_updated_at,
            }
            if connection and connection.ring_battery_level_percent is not None
            else None
        ),
    }


@router.post("/auth-url")
def create_auth_url(current_user: models.User = Depends(get_current_user)):
    try:
        return {"authorization_url": build_authorization_url(current_user.id)}
    except OuraConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/callback")
def oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect(oura="error", reason=error)
    if not code or not state:
        return _frontend_redirect(oura="error", reason="missing_code_or_state")

    try:
        user_id = decode_oauth_state(state)
        save_connection_from_code(db, user_id, code)
    except OuraConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except OuraAPIError:
        return _frontend_redirect(oura="error", reason="authorization_failed")

    try:
        sync_oura_data(db, user_id)
    except OuraAPIError:
        return _frontend_redirect(oura="connected", sync="warning")

    return _frontend_redirect(oura="connected")


@router.post("/sync")
def sync(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return sync_oura_data(db, current_user.id, start_date=start_date, end_date=end_date)
    except OuraConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except OuraAPIError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/daily")
def daily_metrics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    rows = (
        db.query(OuraDailyMetric)
        .filter(
            OuraDailyMetric.user_id == current_user.id,
            OuraDailyMetric.day >= start_date.isoformat(),
            OuraDailyMetric.day <= end_date.isoformat(),
        )
        .order_by(OuraDailyMetric.day.asc())
        .all()
    )
    return [_metric_payload(row) for row in rows]


@router.get("/health-summary")
def health_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    timezone_name: str = Query("Europe/Prague", alias="timezone"),
    locale: str = Query("cs", pattern="^(cs|en)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _build_summary(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
        timezone_name=timezone_name,
        locale=locale,
    )


@router.post("/coach")
def health_coach(
    start_date: date = Query(...),
    end_date: date = Query(...),
    timezone_name: str = Query("Europe/Prague", alias="timezone"),
    locale: str = Query("cs", pattern="^(cs|en)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = _build_summary(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
        timezone_name=timezone_name,
        locale=locale,
    )
    summary["now_local"] = _now_for_timezone(timezone_name)
    return generate_health_coach(summary, locale=locale)


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(OuraDailyMetric).filter(OuraDailyMetric.user_id == current_user.id).delete()
    connection = db.query(OuraConnection).filter(OuraConnection.user_id == current_user.id).first()
    if connection:
        db.delete(connection)
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if profile:
        profile.adaptive_calories_enabled = False
        profile.adaptive_target_calories = None
        profile.adaptive_target_updated_on = None
    db.commit()
    return None
