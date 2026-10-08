"""Read-only Google Health v4 integration, with consent and reconciled data."""
import base64
import hashlib
import json
import secrets
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from .google_health_models import GoogleHealthConnection, GoogleHealthOAuthState, GoogleHealthRecord
from .oura_service import decrypt_token, encrypt_token
from .settings import settings

API_BASE = "https://health.googleapis.com/v4/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE_BASE = "https://www.googleapis.com/auth/googlehealth."
# endpoint id: (JSON union field, filter field, scope suffix)
DATA_TYPES = {
    "steps": ("steps", "steps.interval.civil_start_time", "activity_and_fitness.readonly"),
    "exercise": ("exercise", "exercise.interval.civil_start_time", "activity_and_fitness.readonly"),
    "sleep": ("sleep", "sleep.interval.civil_end_time", "sleep.readonly"),
    "weight": ("weight", "weight.sample_time.civil_time", "health_metrics_and_measurements.readonly"),
    "body-fat": ("bodyFat", "body_fat.sample_time.civil_time", "health_metrics_and_measurements.readonly"),
    "daily-resting-heart-rate": ("dailyRestingHeartRate", "daily_resting_heart_rate.date", "health_metrics_and_measurements.readonly"),
    "daily-heart-rate-variability": ("dailyHeartRateVariability", "daily_heart_rate_variability.date", "health_metrics_and_measurements.readonly"),
}
SCOPES = sorted({SCOPE_BASE + spec[2] for spec in DATA_TYPES.values()})


class GoogleHealthError(RuntimeError):
    def __init__(self, reason: str, status: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def configured() -> bool:
    return all((settings.GOOGLE_HEALTH_CLIENT_ID, settings.GOOGLE_HEALTH_CLIENT_SECRET,
                settings.GOOGLE_HEALTH_REDIRECT_URI)) and settings.JWT_SECRET != "change-me-in-production"


def require_configured():
    if not configured():
        raise GoogleHealthError("NOT_CONFIGURED", 503)


def request_json(url: str, *, token: str | None = None, form: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if form is not None:
        data = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
            body = json.loads(response.read() or b"{}")
            if not isinstance(body, dict):
                raise GoogleHealthError("INVALID_PROVIDER_DATA", 502)
            return body
    except HTTPError as exc:
        # Never expose raw provider responses or credentials to logs/the frontend.
        try:
            body = json.load(exc)
        except (ValueError, TypeError):
            body = {}
        error = body.get("error", {})
        reason = error if isinstance(error, str) else error.get("status", "PROVIDER_ERROR")
        if isinstance(error, dict):
            for detail in error.get("details", []):
                if detail.get("reason") == "ACCOUNT_NOT_LINKED":
                    reason = "ACCOUNT_NOT_LINKED"
        allowed = {"ACCOUNT_NOT_LINKED", "invalid_grant", "access_denied", "PERMISSION_DENIED", "UNAUTHENTICATED", "RESOURCE_EXHAUSTED"}
        raise GoogleHealthError(reason if reason in allowed else "PROVIDER_ERROR", exc.code) from None
    except (URLError, TimeoutError, ValueError):
        raise GoogleHealthError("PROVIDER_UNAVAILABLE", 502) from None


def authorization_url(db: Session, user_id: int) -> str:
    require_configured()
    now = datetime.now(timezone.utc)
    db.query(GoogleHealthOAuthState).filter(GoogleHealthOAuthState.expires_at < now).delete()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    db.add(GoogleHealthOAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(),
                                 user_id=user_id, verifier_encrypted=encrypt_token(verifier),
                                 expires_at=now + timedelta(minutes=10)))
    db.commit()
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": settings.GOOGLE_HEALTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_HEALTH_REDIRECT_URI,
        "response_type": "code", "scope": " ".join(SCOPES), "state": state,
        "access_type": "offline", "prompt": "consent", "code_challenge": challenge,
        "code_challenge_method": "S256",
    })


def complete_authorization(db: Session, code: str, state: str):
    require_configured()
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    row = db.get(GoogleHealthOAuthState, state_hash)
    if not row or row.expires_at <= datetime.now(timezone.utc):
        raise GoogleHealthError("INVALID_STATE")
    user_id = row.user_id
    verifier = decrypt_token(row.verifier_encrypted)
    # Atomic consumption prevents callback replay across processes.
    consumed = db.query(GoogleHealthOAuthState).filter_by(state_hash=state_hash).delete()
    db.commit()
    if consumed != 1:
        raise GoogleHealthError("INVALID_STATE")
    tokens = request_json(TOKEN_URL, form={
        "client_id": settings.GOOGLE_HEALTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_HEALTH_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_HEALTH_REDIRECT_URI,
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
    })
    scopes = set(tokens.get("scope", "").split()) & set(SCOPES)
    if not scopes:
        raise GoogleHealthError("MISSING_PERMISSIONS")
    if not tokens.get("access_token"):
        raise GoogleHealthError("PROVIDER_ERROR", 502)
    identity = request_json(API_BASE + "/identity", token=tokens["access_token"])
    if not identity.get("healthUserId"):
        raise GoogleHealthError("ACCOUNT_NOT_LINKED")
    connection = db.get(GoogleHealthConnection, user_id)
    same_account = connection and connection.health_user_id == identity["healthUserId"]
    if not tokens.get("refresh_token") and not (same_account and connection.refresh_token_encrypted):
        raise GoogleHealthError("OFFLINE_ACCESS_REQUIRED")
    if connection is None:
        connection = GoogleHealthConnection(user_id=user_id)
        db.add(connection)
    if not same_account:
        db.query(GoogleHealthRecord).filter_by(user_id=user_id).delete()
        connection.last_sync_at = None
    # Remove data whose consent has been withdrawn on reauthorization.
    for data_type, spec in DATA_TYPES.items():
        if SCOPE_BASE + spec[2] not in scopes:
            db.query(GoogleHealthRecord).filter_by(user_id=user_id, data_type=data_type).delete()
    connection.health_user_id = identity["healthUserId"]
    connection.access_token_encrypted = encrypt_token(tokens["access_token"])
    if tokens.get("refresh_token"):
        connection.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
    connection.scope = " ".join(sorted(scopes))
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    db.commit()


def access_token(db: Session, connection: GoogleHealthConnection, *, force: bool = False) -> str:
    if not force and connection.token_expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
        return decrypt_token(connection.access_token_encrypted)
    if not connection.refresh_token_encrypted:
        raise GoogleHealthError("RECONNECT_REQUIRED", 409)
    try:
        tokens = request_json(TOKEN_URL, form={
            "client_id": settings.GOOGLE_HEALTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_HEALTH_CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": decrypt_token(connection.refresh_token_encrypted),
        })
    except GoogleHealthError as exc:
        if exc.reason == "invalid_grant":
            raise GoogleHealthError("RECONNECT_REQUIRED", 409) from None
        raise
    if not tokens.get("access_token"):
        raise GoogleHealthError("PROVIDER_ERROR", 502)
    connection.access_token_encrypted = encrypt_token(tokens["access_token"])
    if tokens.get("refresh_token"):
        connection.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
    if "scope" in tokens:
        connection.scope = " ".join(sorted(set(tokens["scope"].split()) & set(SCOPES)))
        for data_type, spec in DATA_TYPES.items():
            if SCOPE_BASE + spec[2] not in connection.scope.split():
                db.query(GoogleHealthRecord).filter_by(user_id=connection.user_id, data_type=data_type).delete()
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    db.commit()
    return tokens["access_token"]


def validate_range(start: date, end: date):
    if end < start or (end - start).days >= 90:
        raise GoogleHealthError("Select a date range of 1 to 90 days.", 422)


def _date_key(value: dict) -> str:
    return date(int(value["year"]), int(value["month"]), int(value["day"])).isoformat()


def record_day(point: dict, data_type: str) -> str:
    value = point[DATA_TYPES[data_type][0]]
    if "date" in value:
        return _date_key(value["date"])
    interval = value.get("interval", {})
    sample = value.get("sampleTime", {})
    civil = interval.get("civilEndTime" if data_type == "sleep" else "civilStartTime", sample.get("civilTime", {}))
    if civil.get("date"):
        return _date_key(civil["date"])
    timestamp = interval.get("endTime" if data_type == "sleep" else "startTime", sample.get("physicalTime"))
    offset = interval.get("endUtcOffset" if data_type == "sleep" else "startUtcOffset", sample.get("utcOffset", "0s"))
    physical = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return (physical + timedelta(seconds=float(offset.rstrip("s")))).date().isoformat()


def fetch_records(token: str, data_type: str, start: date, end: date) -> list[dict]:
    field = DATA_TYPES[data_type][1]
    params = {"filter": f'{field} >= "{start.isoformat()}" AND {field} < "{(end + timedelta(days=1)).isoformat()}"',
              "pageSize": 25 if data_type in {"sleep", "exercise"} else 10000}
    records, seen = [], set()
    for _ in range(200):
        body = request_json(f"{API_BASE}/dataTypes/{data_type}/dataPoints:reconcile?" + urlencode(params), token=token)
        records.extend(body.get("dataPoints", []))
        if len(records) > 50000:
            raise GoogleHealthError("SYNC_TOO_LARGE", 422)
        next_page = body.get("nextPageToken")
        if not next_page:
            return records
        if next_page in seen:
            break
        seen.add(next_page)
        params["pageToken"] = next_page
    raise GoogleHealthError("SYNC_TOO_LARGE", 422)


def sync_data(db: Session, user_id: int, start: date, end: date) -> dict:
    require_configured()
    validate_range(start, end)
    connection = db.get(GoogleHealthConnection, user_id)
    if not connection:
        raise GoogleHealthError("NOT_CONNECTED", 409)
    token = access_token(db, connection)
    if not set(connection.scope.split()) & set(SCOPES):
        raise GoogleHealthError("MISSING_PERMISSIONS", 409)
    synced, warnings = {}, {}
    for data_type, spec in DATA_TYPES.items():
        if SCOPE_BASE + spec[2] not in connection.scope.split():
            warnings[data_type] = "MISSING_PERMISSIONS"
            continue
        try:
            try:
                points = fetch_records(token, data_type, start, end)
            except GoogleHealthError as exc:
                if exc.status != 401:
                    raise
                token = access_token(db, connection, force=True)
                points = fetch_records(token, data_type, start, end)
            normalized = {}
            for point in points:
                day = record_day(point, data_type)
                if not start.isoformat() <= day <= end.isoformat():
                    continue
                payload = json.dumps(point, sort_keys=True)
                key = point.get("dataPointName") or point.get("name") or hashlib.sha256(payload.encode()).hexdigest()
                daily_summary([GoogleHealthRecord(day=day, data_type=data_type, payload_json=payload)])
                normalized[key] = (day, payload)
        except GoogleHealthError as exc:
            if exc.reason in {"RECONNECT_REQUIRED", "ACCOUNT_NOT_LINKED"}:
                raise
            warnings[data_type] = exc.reason
            continue
        except (KeyError, ValueError, TypeError, AttributeError):
            warnings[data_type] = "INVALID_PROVIDER_DATA"
            continue
        # Replace only a fully downloaded type/range. Failed pages preserve old data.
        db.query(GoogleHealthRecord).filter(
            GoogleHealthRecord.user_id == user_id, GoogleHealthRecord.data_type == data_type,
            GoogleHealthRecord.day >= start.isoformat(), GoogleHealthRecord.day <= end.isoformat(),
        ).delete(synchronize_session=False)
        for key, (day, payload) in normalized.items():
            existing = db.query(GoogleHealthRecord).filter_by(user_id=user_id, data_type=data_type, record_key=key).first()
            if existing:
                existing.day, existing.payload_json = day, payload
            else:
                db.add(GoogleHealthRecord(user_id=user_id, data_type=data_type, record_key=key, day=day, payload_json=payload))
        db.commit()
        synced[data_type] = len(normalized)
    if synced:
        connection.last_sync_at = datetime.now(timezone.utc)
        db.commit()
    if not synced:
        raise GoogleHealthError("SYNC_FAILED", 502)
    return {"synced": synced, "warnings": warnings, "last_sync_at": connection.last_sync_at}


def query_records(db: Session, user_id: int, start: date, end: date):
    validate_range(start, end)
    return db.query(GoogleHealthRecord).filter(
        GoogleHealthRecord.user_id == user_id,
        GoogleHealthRecord.day >= start.isoformat(), GoogleHealthRecord.day <= end.isoformat(),
    ).order_by(GoogleHealthRecord.day, GoogleHealthRecord.id).all()


def daily_summary(rows) -> list[dict]:
    days = {}
    for row in rows:
        day = days.setdefault(row.day, {"day": row.day})
        value = json.loads(row.payload_json)[DATA_TYPES[row.data_type][0]]
        if row.data_type == "steps":
            day["steps"] = day.get("steps", 0) + int(value["count"])
        elif row.data_type == "sleep" and "minutesAsleep" in value.get("summary", {}):
            day["sleep_minutes"] = day.get("sleep_minutes", 0) + int(value["summary"]["minutesAsleep"])
        elif row.data_type == "daily-resting-heart-rate":
            day["resting_heart_rate_bpm"] = float(value["beatsPerMinute"])
        elif row.data_type == "daily-heart-rate-variability" and "averageHeartRateVariabilityMilliseconds" in value:
            day["hrv_ms"] = float(value["averageHeartRateVariabilityMilliseconds"])
        elif row.data_type == "weight":
            timestamp = value.get("sampleTime", {}).get("physicalTime", "")
            if timestamp >= day.get("_weight_time", ""):
                day["weight_kg"] = float(value["weightGrams"]) / 1000
                day["_weight_time"] = timestamp
        elif row.data_type == "body-fat":
            timestamp = value.get("sampleTime", {}).get("physicalTime", "")
            if timestamp >= day.get("_fat_time", ""):
                day["body_fat_percent"] = float(value["percentage"])
                day["_fat_time"] = timestamp
        elif row.data_type == "exercise":
            day["workouts"] = day.get("workouts", 0) + 1
    return [{key: value for key, value in day.items() if not key.startswith("_")} for _, day in sorted(days.items())]
