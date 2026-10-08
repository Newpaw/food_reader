import json
import secrets
from datetime import date
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..deps import get_current_user, get_db
from ..google_health_models import GoogleHealthConnection, GoogleHealthOAuthState, GoogleHealthRecord
from .. import google_health_service as service
from ..settings import settings

router = APIRouter(prefix="/google-health", tags=["google-health"])


@router.get("/status")
def connection_status(response: Response, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    connection = db.get(GoogleHealthConnection, user.id)
    scopes = connection.scope.split() if connection else []
    return {"configured": service.configured(), "connected": connection is not None,
            "last_sync_at": connection.last_sync_at if connection else None,
            "record_count": db.query(GoogleHealthRecord).filter_by(user_id=user.id).count(),
            "available_types": [name for name, spec in service.DATA_TYPES.items() if service.SCOPE_BASE + spec[2] in scopes],
            "missing_scopes": sorted(set(service.SCOPES) - set(scopes)) if connection else []}


@router.post("/auth-url")
def auth_url(response: Response, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        url = service.authorization_url(db, user.id)
        state = parse_qs(urlparse(url).query)["state"][0]
        response.set_cookie("google_health_state", state, max_age=600, httponly=True,
                            secure=settings.GOOGLE_HEALTH_REDIRECT_URI.startswith("https://"),
                            samesite="lax", path="/google-health")
        response.headers["Cache-Control"] = "no-store"
        return {"authorization_url": url}
    except service.GoogleHealthError as exc:
        raise HTTPException(exc.status, detail=exc.reason) from None


@router.get("/callback")
def callback(code: str | None = None, state: str | None = None, error: str | None = None,
             db: Session = Depends(get_db), google_health_state: str | None = Cookie(None)):
    result = "connected"
    if not state or not google_health_state or not secrets.compare_digest(state, google_health_state):
        result = "INVALID_STATE"
    elif error:
        result = "access_denied"
    elif not code or not state:
        result = "INVALID_STATE"
    else:
        try:
            service.complete_authorization(db, code, state)
        except service.GoogleHealthError as exc:
            db.rollback()
            result = exc.reason
    # Fixed local destination; never reflect arbitrary redirect/error parameters.
    response = RedirectResponse("/google-health.html?" + urlencode({"google_health": result}),
                            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    response.delete_cookie("google_health_state", path="/google-health")
    return response


@router.post("/sync")
def sync(start_date: date = Query(...), end_date: date = Query(...),
         user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return service.sync_data(db, user.id, start_date, end_date)
    except service.GoogleHealthError as exc:
        db.rollback()
        raise HTTPException(exc.status if exc.status in {409, 422, 503} else 502, detail=exc.reason) from None


@router.get("/data")
def data(start_date: date = Query(...), end_date: date = Query(...),
         user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        rows = service.query_records(db, user.id, start_date, end_date)
        payload = {"daily": service.daily_summary(rows),
                   "records": [{"day": row.day, "data_type": row.data_type, "data": json.loads(row.payload_json)} for row in rows]}
        return Response(json.dumps(payload), media_type="application/json", headers={"Cache-Control": "no-store"})
    except service.GoogleHealthError as exc:
        raise HTTPException(exc.status, detail=exc.reason) from None


@router.get("/export")
def export(start_date: date = Query(...), end_date: date = Query(...),
           user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = data(start_date, end_date, user, db)
    response.headers["Content-Disposition"] = f'attachment; filename="google-health-{start_date}-{end_date}.json"'
    return response


@router.delete("/disconnect", status_code=204)
def disconnect(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = db.get(GoogleHealthConnection, user.id)
    if connection:
        try:
            service.request_json("https://oauth2.googleapis.com/revoke", form={
                "token": service.decrypt_token(connection.refresh_token_encrypted or connection.access_token_encrypted)})
        except service.GoogleHealthError as exc:
            # Invalid/already revoked grants are safe to remove; retry transient failures.
            if exc.status not in {400, 401}:
                raise HTTPException(502, detail="REVOCATION_FAILED") from None
        db.delete(connection)
    db.query(GoogleHealthRecord).filter_by(user_id=user.id).delete()
    db.query(GoogleHealthOAuthState).filter_by(user_id=user.id).delete()
    db.commit()
