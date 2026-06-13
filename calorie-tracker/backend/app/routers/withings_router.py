from datetime import timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db
from ..settings import settings
from ..withings_service import (
    WithingsAPIError,
    WithingsConfigError,
    build_authorization_url,
    decode_oauth_state,
    latest_weight_measurement,
    save_connection_from_code,
    sync_measurements,
    withings_configured,
)


router = APIRouter(prefix="/withings", tags=["withings"])


def _service_unavailable_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def _frontend_redirect(**params: str) -> RedirectResponse:
    separator = "&" if "?" in settings.APP_FRONTEND_URL else "?"
    return RedirectResponse(f"{settings.APP_FRONTEND_URL}{separator}{urlencode(params)}")


@router.get("/status", response_model=schemas.WithingsStatusOut)
def get_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = (
        db.query(models.WithingsConnection)
        .filter(models.WithingsConnection.user_id == current_user.id)
        .first()
    )
    latest = latest_weight_measurement(db, current_user.id)
    return schemas.WithingsStatusOut(
        configured=withings_configured(),
        connected=connection is not None,
        last_sync_at=connection.last_sync_at if connection else None,
        latest_weight_kg=latest.weight_kg if latest else None,
        latest_measured_at=latest.measured_at if latest else None,
        scope=connection.scope if connection else None,
    )


@router.post("/auth-url", response_model=schemas.WithingsAuthUrlOut)
def create_auth_url(current_user: models.User = Depends(get_current_user)):
    try:
        return schemas.WithingsAuthUrlOut(authorization_url=build_authorization_url(current_user.id))
    except WithingsConfigError as exc:
        raise _service_unavailable_error(exc) from exc


@router.get("/callback")
def oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect(withings="error", reason=error)
    if not code or not state:
        return _frontend_redirect(withings="error", reason="missing_code_or_state")

    try:
        user_id = decode_oauth_state(state)
        save_connection_from_code(db, user_id, code)
    except WithingsConfigError as exc:
        raise _service_unavailable_error(exc) from exc
    except WithingsAPIError:
        return _frontend_redirect(withings="error", reason="authorization_failed")

    return _frontend_redirect(withings="connected")


@router.post("/sync", response_model=schemas.WithingsSyncOut)
def sync_withings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return sync_measurements(db, current_user.id)
    except WithingsConfigError as exc:
        raise _service_unavailable_error(exc) from exc
    except WithingsAPIError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/measurements", response_model=list[schemas.WithingsMeasurementOut])
def list_measurements(
    frm: AwareDatetime | None = Query(None),
    to: AwareDatetime | None = Query(None),
    limit: int = Query(100, ge=1, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.WithingsMeasurement).filter(models.WithingsMeasurement.user_id == current_user.id)
    if frm:
        query = query.filter(models.WithingsMeasurement.measured_at >= frm.astimezone(timezone.utc))
    if to:
        query = query.filter(models.WithingsMeasurement.measured_at < to.astimezone(timezone.utc))
    return query.order_by(models.WithingsMeasurement.measured_at.desc()).limit(limit).all()


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(models.WithingsMeasurement).filter(models.WithingsMeasurement.user_id == current_user.id).delete()
    connection = (
        db.query(models.WithingsConnection)
        .filter(models.WithingsConnection.user_id == current_user.id)
        .first()
    )
    if connection:
        db.delete(connection)
    db.commit()
    return None
