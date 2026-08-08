import base64
import hashlib
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from .oura_models import OuraConnection, OuraDailyMetric
from .settings import settings


OURA_AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
OURA_TOKEN_URL = "https://api.ouraring.com/oauth/token"
OURA_API_BASE = "https://api.ouraring.com/v2/usercollection"
OURA_SCOPE = "daily workout personal"
INITIAL_SYNC_DAYS = 365
INCREMENTAL_LOOKBACK_DAYS = 7


class OuraConfigError(RuntimeError):
    pass


class OuraAPIError(RuntimeError):
    pass


def oura_configured() -> bool:
    return all([settings.OURA_CLIENT_ID, settings.OURA_CLIENT_SECRET, settings.OURA_REDIRECT_URI])


def ensure_oura_configured() -> None:
    if not oura_configured():
        raise OuraConfigError("Oura integration is not configured.")


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def build_oauth_state(user_id: int, expires_in_seconds: int = 600) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + expires_in_seconds,
            "type": "oura_oauth",
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALG,
    )


def decode_oauth_state(state: str) -> int:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.PyJWTError as exc:
        raise OuraAPIError("Invalid or expired Oura authorization state.") from exc
    if payload.get("type") != "oura_oauth" or not payload.get("sub"):
        raise OuraAPIError("Invalid Oura authorization state.")
    return int(payload["sub"])


def build_authorization_url(user_id: int) -> str:
    ensure_oura_configured()
    params = {
        "response_type": "code",
        "client_id": settings.OURA_CLIENT_ID,
        "redirect_uri": settings.OURA_REDIRECT_URI,
        "scope": OURA_SCOPE,
        "state": build_oauth_state(user_id),
    }
    return f"{OURA_AUTH_URL}?{urlencode(params)}"


def _json_request(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    access_token: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = urlencode({key: value for key, value in data.items() if value is not None}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = detail.get("detail") or detail.get("title") or detail.get("error_description") or detail.get("error")
        except Exception:
            message = None
        raise OuraAPIError(message or f"Oura API returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise OuraAPIError(f"Unable to reach Oura API: {exc.reason}") from exc


class OuraClient:
    def exchange_code(self, code: str) -> dict[str, Any]:
        ensure_oura_configured()
        payload = _json_request(
            OURA_TOKEN_URL,
            method="POST",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.OURA_CLIENT_ID,
                "client_secret": settings.OURA_CLIENT_SECRET,
                "redirect_uri": settings.OURA_REDIRECT_URI,
            },
        )
        return self._validate_token_payload(payload)

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        ensure_oura_configured()
        payload = _json_request(
            OURA_TOKEN_URL,
            method="POST",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.OURA_CLIENT_ID,
                "client_secret": settings.OURA_CLIENT_SECRET,
            },
        )
        return self._validate_token_payload(payload)

    @staticmethod
    def _validate_token_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("access_token") or not payload.get("refresh_token"):
            raise OuraAPIError("Oura token response did not include required tokens.")
        return payload

    def fetch_collection(
        self,
        access_token: str,
        endpoint: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "next_token": next_token,
            }
            payload = _json_request(
                f"{OURA_API_BASE}/{endpoint}?{urlencode({k: v for k, v in params.items() if v})}",
                access_token=access_token,
            )
            rows.extend(payload.get("data") or [])
            next_token = payload.get("next_token")
            if not next_token:
                return rows

    def fetch_personal_info(self, access_token: str) -> dict[str, Any]:
        return _json_request(f"{OURA_API_BASE}/personal_info", access_token=access_token)


def _store_tokens(connection: OuraConnection, token_payload: dict[str, Any]) -> None:
    connection.access_token_encrypted = encrypt_token(token_payload["access_token"])
    connection.refresh_token_encrypted = encrypt_token(token_payload["refresh_token"])
    connection.scope = token_payload.get("scope") or connection.scope
    expires_in = int(token_payload.get("expires_in") or 0)
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None
    connection.updated_at = datetime.now(timezone.utc)


def save_connection_from_code(
    db: Session,
    user_id: int,
    code: str,
    *,
    client: OuraClient | None = None,
) -> OuraConnection:
    active_client = client or OuraClient()
    token_payload = active_client.exchange_code(code)
    connection = db.query(OuraConnection).filter(OuraConnection.user_id == user_id).first()
    if connection is None:
        connection = OuraConnection(
            user_id=user_id,
            access_token_encrypted=encrypt_token(token_payload["access_token"]),
            refresh_token_encrypted=encrypt_token(token_payload["refresh_token"]),
        )
        db.add(connection)
    _store_tokens(connection, token_payload)

    try:
        personal = active_client.fetch_personal_info(token_payload["access_token"])
        if personal.get("id"):
            connection.oura_user_id = str(personal["id"])
    except OuraAPIError:
        pass

    db.commit()
    db.refresh(connection)
    return connection


def get_valid_access_token(
    db: Session,
    connection: OuraConnection,
    *,
    client: OuraClient | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if connection.token_expires_at and connection.token_expires_at > now + timedelta(minutes=2):
        return decrypt_token(connection.access_token_encrypted)

    active_client = client or OuraClient()
    token_payload = active_client.refresh_access_token(decrypt_token(connection.refresh_token_encrypted))
    _store_tokens(connection, token_payload)
    db.commit()
    db.refresh(connection)
    return decrypt_token(connection.access_token_encrypted)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _duration_seconds(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str):
        try:
            return max(0, int(float(value)))
        except ValueError:
            match = re.fullmatch(r"PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?", value)
            if match:
                hours = float(match.group(1) or 0)
                minutes = float(match.group(2) or 0)
                seconds = float(match.group(3) or 0)
                return int(hours * 3600 + minutes * 60 + seconds)
    return 0


def _metric(db: Session, user_id: int, day: str) -> OuraDailyMetric:
    metric = (
        db.query(OuraDailyMetric)
        .filter(OuraDailyMetric.user_id == user_id, OuraDailyMetric.day == day)
        .first()
    )
    if metric is None:
        metric = OuraDailyMetric(user_id=user_id, day=day)
        db.add(metric)
    metric.updated_at = datetime.now(timezone.utc)
    return metric


def _day_from_row(row: dict[str, Any]) -> str | None:
    day = row.get("day")
    if isinstance(day, str) and len(day) >= 10:
        return day[:10]
    for key in ("start_datetime", "timestamp"):
        value = row.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]
    return None


def sync_oura_data(
    db: Session,
    user_id: int,
    *,
    client: OuraClient | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    connection = db.query(OuraConnection).filter(OuraConnection.user_id == user_id).first()
    if connection is None:
        raise OuraAPIError("Oura account is not connected.")

    active_client = client or OuraClient()
    access_token = get_valid_access_token(db, connection, client=active_client)
    today = datetime.now(timezone.utc).date()
    sync_end = end_date or today
    if start_date:
        sync_start = start_date
    elif connection.last_sync_at:
        sync_start = max(sync_end - timedelta(days=INCREMENTAL_LOOKBACK_DAYS), connection.last_sync_at.date() - timedelta(days=1))
    else:
        sync_start = sync_end - timedelta(days=INITIAL_SYNC_DAYS)

    if sync_start > sync_end:
        sync_start = sync_end

    warnings: list[str] = []
    core = {
        "daily_activity": active_client.fetch_collection(access_token, "daily_activity", start_date=sync_start, end_date=sync_end),
        "daily_readiness": active_client.fetch_collection(access_token, "daily_readiness", start_date=sync_start, end_date=sync_end),
        "daily_sleep": active_client.fetch_collection(access_token, "daily_sleep", start_date=sync_start, end_date=sync_end),
    }

    optional: dict[str, list[dict[str, Any]]] = {}
    for endpoint in ("sleep", "daily_stress", "workout"):
        try:
            optional[endpoint] = active_client.fetch_collection(
                access_token,
                endpoint,
                start_date=sync_start,
                end_date=sync_end,
            )
        except OuraAPIError as exc:
            optional[endpoint] = []
            warnings.append(f"{endpoint}: {exc}")

    touched_days: set[str] = set()

    for row in core["daily_activity"]:
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.activity_score = _as_int(row.get("score"))
        metric.active_calories = _as_int(row.get("active_calories"))
        metric.total_calories = _as_int(row.get("total_calories"))
        metric.steps = _as_int(row.get("steps"))
        touched_days.add(day)

    for row in core["daily_readiness"]:
        day = _day_from_row(row)
        if not day:
            continue
        _metric(db, user_id, day).readiness_score = _as_int(row.get("score"))
        touched_days.add(day)

    for row in core["daily_sleep"]:
        day = _day_from_row(row)
        if not day:
            continue
        _metric(db, user_id, day).sleep_score = _as_int(row.get("score"))
        touched_days.add(day)

    sleep_by_day: dict[str, dict[str, Any]] = {}
    for row in optional["sleep"]:
        day = _day_from_row(row)
        if not day:
            continue
        current = sleep_by_day.get(day)
        if current is None or _duration_seconds(row.get("total_sleep_duration")) > _duration_seconds(current.get("total_sleep_duration")):
            sleep_by_day[day] = row
    for day, row in sleep_by_day.items():
        metric = _metric(db, user_id, day)
        metric.total_sleep_seconds = _duration_seconds(row.get("total_sleep_duration")) or None
        metric.average_hrv_ms = _as_float(row.get("average_hrv"))
        metric.lowest_heart_rate_bpm = _as_int(row.get("lowest_heart_rate"))
        touched_days.add(day)

    for row in optional["daily_stress"]:
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.stress_high_seconds = _as_int(row.get("stress_high"))
        metric.recovery_high_seconds = _as_int(row.get("recovery_high"))
        touched_days.add(day)

    workout_totals: dict[str, dict[str, float]] = {}
    for row in optional["workout"]:
        day = _day_from_row(row)
        if not day:
            continue
        totals = workout_totals.setdefault(day, {"count": 0.0, "calories": 0.0, "seconds": 0.0})
        totals["count"] += 1
        totals["calories"] += _as_float(row.get("calories")) or 0.0
        totals["seconds"] += _duration_seconds(row.get("duration"))
    for day, totals in workout_totals.items():
        metric = _metric(db, user_id, day)
        metric.workout_count = int(totals["count"])
        metric.workout_calories = round(totals["calories"], 1)
        metric.workout_seconds = int(totals["seconds"])
        touched_days.add(day)

    connection.last_sync_at = datetime.now(timezone.utc)
    connection.updated_at = connection.last_sync_at
    db.commit()

    return {
        "synced_days": len(touched_days),
        "start_date": sync_start.isoformat(),
        "end_date": sync_end.isoformat(),
        "last_sync_at": connection.last_sync_at,
        "warnings": warnings,
    }
