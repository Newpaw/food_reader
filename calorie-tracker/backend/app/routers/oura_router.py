from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..deps import get_current_user, get_db
from ..health_service import build_health_summary
from ..oura_models import OuraConnection, OuraDailyMetric
from ..oura_service import (
    OuraAPIError,
    OuraConfigError,
    build_authorization_url,
    decode_oauth_state,
    oura_configured,
    save_connection_from_code,
    sync_oura_data,
)
from ..settings import settings


router = APIRouter(prefix="/oura", tags=["oura"])


def _frontend_redirect(**params: str) -> RedirectResponse:
    separator = "&" if "?" in settings.OURA_FRONTEND_URL else "?"
    return RedirectResponse(f"{settings.OURA_FRONTEND_URL}{separator}{urlencode(params)}")


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
    return {
        "configured": oura_configured(),
        "connected": connection is not None,
        "scope": connection.scope if connection else None,
        "last_sync_at": connection.last_sync_at if connection else None,
        "synced_days": metric_count,
        "latest_day": latest.day if latest else None,
        "latest_readiness": latest.readiness_score if latest else None,
        "latest_sleep_score": latest.sleep_score if latest else None,
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
    return [
        {
            "day": row.day,
            "activity_score": row.activity_score,
            "active_calories": row.active_calories,
            "total_calories": row.total_calories,
            "steps": row.steps,
            "readiness_score": row.readiness_score,
            "sleep_score": row.sleep_score,
            "total_sleep_seconds": row.total_sleep_seconds,
            "average_hrv_ms": row.average_hrv_ms,
            "lowest_heart_rate_bpm": row.lowest_heart_rate_bpm,
            "stress_high_seconds": row.stress_high_seconds,
            "recovery_high_seconds": row.recovery_high_seconds,
            "workout_count": row.workout_count,
            "workout_calories": row.workout_calories,
            "workout_seconds": row.workout_seconds,
        }
        for row in rows
    ]


@router.get("/health-summary")
def health_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    timezone_name: str = Query("Europe/Prague", alias="timezone"),
    locale: str = Query("cs", pattern="^(cs|en)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return build_health_summary(
            db,
            current_user.id,
            start_date=start_date,
            end_date=end_date,
            timezone_name=timezone_name,
            locale=locale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(OuraDailyMetric).filter(OuraDailyMetric.user_id == current_user.id).delete()
    connection = db.query(OuraConnection).filter(OuraConnection.user_id == current_user.id).first()
    if connection:
        db.delete(connection)
    db.commit()
    return None
