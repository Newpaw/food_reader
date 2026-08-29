import base64
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
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
OURA_SCOPE = "daily workout personal heartrate tag session spo2Daily"
RECOMMENDED_SCOPES = {"daily", "workout", "personal", "heartrate", "tag", "session", "spo2Daily"}
INITIAL_SYNC_DAYS = 365
INCREMENTAL_LOOKBACK_DAYS = 7
HEART_RATE_INITIAL_DAYS = 30


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


def parse_oura_scopes(scope: str | None) -> set[str]:
    if not scope:
        return set()
    return {part for part in re.split(r"[\s,]+", scope.strip()) if part}


def missing_oura_scopes(connection: OuraConnection | None) -> list[str]:
    if connection is None:
        return sorted(RECOMMENDED_SCOPES)
    granted = parse_oura_scopes(connection.scope)
    # Older Oura auth documentation used `spo2`; accept it as equivalent to
    # the current V2 `spo2Daily` name when evaluating an existing token.
    if "spo2" in granted:
        granted.add("spo2Daily")
    return sorted(RECOMMENDED_SCOPES - granted)


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

    def fetch_timeseries(
        self,
        access_token: str,
        endpoint: str,
        *,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        next_token: str | None = None
        start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        while True:
            params = {
                "start_datetime": start_datetime.isoformat(),
                "end_datetime": end_datetime.isoformat(),
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

    def fetch_unbounded_collection(self, access_token: str, endpoint: str) -> list[dict[str, Any]]:
        """Fetch collections such as ring configuration that do not accept dates."""
        rows: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            params = {"next_token": next_token}
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


def _store_personal_info(connection: OuraConnection, personal: dict[str, Any]) -> None:
    if personal.get("id"):
        connection.oura_user_id = str(personal["id"])
    connection.profile_age = _as_int(personal.get("age"))
    connection.profile_weight_kg = _as_float(personal.get("weight"))
    connection.profile_height_m = _as_float(personal.get("height"))
    connection.profile_biological_sex = (
        str(personal["biological_sex"]) if personal.get("biological_sex") is not None else None
    )


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
        _store_personal_info(connection, personal)
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
        db.flush()
    metric.updated_at = datetime.now(timezone.utc)
    return metric


def _day_from_row(row: dict[str, Any]) -> str | None:
    day = row.get("day") or row.get("start_day")
    if isinstance(day, str) and len(day) >= 10:
        return day[:10]
    for key in ("start_datetime", "timestamp", "start_time"):
        value = row.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]
    return None


def _details(metric: OuraDailyMetric) -> dict[str, Any]:
    if not metric.details_json:
        return {}
    try:
        value = json.loads(metric.details_json)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _set_detail(metric: OuraDailyMetric, key: str, value: Any) -> None:
    if value is None or value == {} or value == []:
        return
    payload = _details(metric)
    payload[key] = value
    metric.details_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_oura_details(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        return payload if isinstance(payload, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _compact_workout(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "activity",
            "label",
            "intensity",
            "calories",
            "duration",
            "start_datetime",
            "end_datetime",
            "distance",
            "source",
        )
        if row.get(key) is not None
    }


def _compact_session(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in ("type", "mood", "start_datetime", "end_datetime", "duration", "motion_count")
        if row.get(key) is not None
    }


def _compact_tag(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "tag_type_code",
            "custom_name",
            "text",
            "comment",
            "start_day",
            "end_day",
            "start_time",
            "end_time",
            "start_datetime",
            "end_datetime",
        )
        if row.get(key) is not None
    }


def _row_duration_seconds(row: dict[str, Any]) -> int:
    explicit = _duration_seconds(row.get("duration"))
    if explicit:
        return explicit
    start = row.get("start_datetime")
    end = row.get("end_datetime")
    if not isinstance(start, str) or not isinstance(end, str):
        return 0
    try:
        start_value = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_value = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, int((end_value - start_value).total_seconds()))


def _compact_ring_configuration(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in ("id", "color", "design", "firmware_version", "hardware_type", "set_up_at", "size")
        if row.get(key) is not None
    }


def _safe_optional_collection(
    client: OuraClient,
    access_token: str,
    endpoint: str,
    *,
    start_date: date,
    end_date: date,
    warnings: list[str],
) -> list[dict[str, Any]]:
    try:
        return client.fetch_collection(access_token, endpoint, start_date=start_date, end_date=end_date)
    except OuraAPIError as exc:
        warnings.append(f"{endpoint}: {exc}")
        return []


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
    granted_scopes = parse_oura_scopes(connection.scope)
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
        optional[endpoint] = _safe_optional_collection(
            active_client,
            access_token,
            endpoint,
            start_date=sync_start,
            end_date=sync_end,
            warnings=warnings,
        )

    # These daily endpoints are deliberately optional: older accounts/apps may
    # not expose every newer Oura metric. A missing endpoint must never block
    # the core sleep/readiness/activity sync.
    if "daily" in granted_scopes:
        for endpoint in (
            "daily_resilience",
            "daily_cardiovascular_age",
            "vO2_max",
            "sleep_time",
            "rest_mode_period",
        ):
            optional[endpoint] = _safe_optional_collection(
                active_client,
                access_token,
                endpoint,
                start_date=sync_start,
                end_date=sync_end,
                warnings=warnings,
            )

    if "personal" in granted_scopes:
        try:
            _store_personal_info(connection, active_client.fetch_personal_info(access_token))
        except OuraAPIError as exc:
            warnings.append(f"personal_info: {exc}")

        try:
            ring_configurations = active_client.fetch_unbounded_collection(access_token, "ring_configuration")
            if ring_configurations:
                connection.ring_configuration_json = json.dumps(
                    [_compact_ring_configuration(row) for row in ring_configurations[:5]],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
        except OuraAPIError as exc:
            warnings.append(f"ring_configuration: {exc}")

        battery_start = max(sync_start, sync_end - timedelta(days=6))
        try:
            battery_rows = active_client.fetch_timeseries(
                access_token,
                "ring_battery_level",
                start_date=battery_start,
                end_date=sync_end,
            )
            if battery_rows:
                latest_battery = max(
                    battery_rows,
                    key=lambda row: (row.get("timestamp_unix") or 0, str(row.get("timestamp") or "")),
                )
                connection.ring_battery_level_percent = _as_int(latest_battery.get("level"))
                connection.ring_battery_charging = latest_battery.get("charging")
                connection.ring_battery_in_charger = latest_battery.get("in_charger")
                timestamp = latest_battery.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        connection.ring_battery_updated_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    except ValueError:
                        pass
        except OuraAPIError as exc:
            warnings.append(f"ring_battery_level: {exc}")

    if "spo2Daily" in granted_scopes or "spo2" in granted_scopes:
        optional["daily_spo2"] = _safe_optional_collection(
            active_client,
            access_token,
            "daily_spo2",
            start_date=sync_start,
            end_date=sync_end,
            warnings=warnings,
        )

    if "session" in granted_scopes:
        optional["session"] = _safe_optional_collection(
            active_client,
            access_token,
            "session",
            start_date=sync_start,
            end_date=sync_end,
            warnings=warnings,
        )

    if "tag" in granted_scopes:
        try:
            optional["tag"] = active_client.fetch_collection(
                access_token,
                "enhanced_tag",
                start_date=sync_start,
                end_date=sync_end,
            )
        except OuraAPIError:
            optional["tag"] = _safe_optional_collection(
                active_client,
                access_token,
                "tag",
                start_date=sync_start,
                end_date=sync_end,
                warnings=warnings,
            )

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
        metric.activity_target_calories = _as_int(row.get("target_calories"))
        metric.average_met_minutes = _as_float(row.get("average_met_minutes"))
        metric.equivalent_walking_distance_m = _as_float(row.get("equivalent_walking_distance"))
        metric.sedentary_seconds = _duration_seconds(row.get("sedentary_time")) or None
        metric.resting_seconds = _duration_seconds(row.get("resting_time")) or None
        metric.low_activity_seconds = _duration_seconds(row.get("low_activity_time")) or None
        metric.medium_activity_seconds = _duration_seconds(row.get("medium_activity_time")) or None
        metric.high_activity_seconds = _duration_seconds(row.get("high_activity_time")) or None
        metric.non_wear_seconds = _duration_seconds(row.get("non_wear_time")) or None
        metric.inactivity_alerts = _as_int(row.get("inactivity_alerts"))
        metric.activity_target_meters = _as_int(row.get("target_meters"))
        metric.activity_meters_to_target = _as_int(row.get("meters_to_target"))
        _set_detail(metric, "activity_contributors", row.get("contributors"))
        _set_detail(
            metric,
            "activity_met_minutes",
            {
                "sedentary": _as_float(row.get("sedentary_met_minutes")),
                "low": _as_float(row.get("low_activity_met_minutes")),
                "medium": _as_float(row.get("medium_activity_met_minutes")),
                "high": _as_float(row.get("high_activity_met_minutes")),
            },
        )
        touched_days.add(day)

    for row in core["daily_readiness"]:
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.readiness_score = _as_int(row.get("score"))
        metric.temperature_deviation_c = _as_float(row.get("temperature_deviation"))
        metric.temperature_trend_deviation_c = _as_float(row.get("temperature_trend_deviation"))
        _set_detail(metric, "readiness_contributors", row.get("contributors"))
        touched_days.add(day)

    for row in core["daily_sleep"]:
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.sleep_score = _as_int(row.get("score"))
        _set_detail(metric, "sleep_contributors", row.get("contributors"))
        touched_days.add(day)

    sleep_by_day: dict[str, dict[str, Any]] = {}
    for row in optional.get("sleep", []):
        day = _day_from_row(row)
        if not day:
            continue
        current = sleep_by_day.get(day)
        if current is None or _duration_seconds(row.get("total_sleep_duration")) > _duration_seconds(current.get("total_sleep_duration")):
            sleep_by_day[day] = row
    for day, row in sleep_by_day.items():
        metric = _metric(db, user_id, day)
        metric.total_sleep_seconds = _duration_seconds(row.get("total_sleep_duration")) or None
        metric.time_in_bed_seconds = _duration_seconds(row.get("time_in_bed")) or None
        metric.awake_seconds = _duration_seconds(row.get("awake_time")) or None
        metric.light_sleep_seconds = _duration_seconds(row.get("light_sleep_duration")) or None
        metric.deep_sleep_seconds = _duration_seconds(row.get("deep_sleep_duration")) or None
        metric.rem_sleep_seconds = _duration_seconds(row.get("rem_sleep_duration")) or None
        metric.sleep_latency_seconds = _duration_seconds(row.get("latency")) or None
        metric.sleep_efficiency = _as_float(row.get("efficiency"))
        metric.average_hrv_ms = _as_float(row.get("average_hrv"))
        metric.lowest_heart_rate_bpm = _as_int(row.get("lowest_heart_rate"))
        metric.average_heart_rate_bpm = _as_float(row.get("average_heart_rate"))
        metric.average_breaths_per_minute = _as_float(row.get("average_breath"))
        metric.bedtime_start = row.get("bedtime_start")
        metric.bedtime_end = row.get("bedtime_end")
        metric.sleep_score_delta = _as_int(row.get("sleep_score_delta"))
        metric.readiness_score_delta = _as_int(row.get("readiness_score_delta"))
        metric.low_battery_alert = row.get("low_battery_alert")
        _set_detail(metric, "sleep_type", row.get("type"))
        _set_detail(metric, "restless_periods", _as_int(row.get("restless_periods")))
        _set_detail(metric, "sleep_algorithm_version", row.get("sleep_algorithm_version"))
        _set_detail(metric, "sleep_analysis_reason", row.get("sleep_analysis_reason"))
        _set_detail(metric, "sleep_readiness", row.get("readiness"))
        touched_days.add(day)

    for row in optional.get("daily_stress", []):
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.stress_high_seconds = _as_int(row.get("stress_high"))
        metric.recovery_high_seconds = _as_int(row.get("recovery_high"))
        _set_detail(metric, "stress_day_summary", row.get("day_summary"))
        touched_days.add(day)

    workout_totals: dict[str, dict[str, Any]] = {}
    for row in optional.get("workout", []):
        day = _day_from_row(row)
        if not day:
            continue
        totals = workout_totals.setdefault(day, {"count": 0, "calories": 0.0, "seconds": 0, "items": []})
        totals["count"] += 1
        totals["calories"] += _as_float(row.get("calories")) or 0.0
        totals["seconds"] += _row_duration_seconds(row)
        totals["items"].append(_compact_workout(row))
    for day, totals in workout_totals.items():
        metric = _metric(db, user_id, day)
        metric.workout_count = int(totals["count"])
        metric.workout_calories = round(float(totals["calories"]), 1)
        metric.workout_seconds = int(totals["seconds"])
        _set_detail(metric, "workouts", totals["items"][:12])
        touched_days.add(day)

    for row in optional.get("daily_spo2", []):
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        percentage = row.get("spo2_percentage")
        if isinstance(percentage, dict):
            metric.spo2_average_percent = _as_float(percentage.get("average"))
            _set_detail(metric, "spo2", percentage)
        else:
            metric.spo2_average_percent = _as_float(row.get("average"))
        metric.breathing_disturbance_index = _as_int(row.get("breathing_disturbance_index"))
        touched_days.add(day)

    for row in optional.get("daily_resilience", []):
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.resilience_level = str(row.get("level")) if row.get("level") is not None else None
        _set_detail(metric, "resilience_contributors", row.get("contributors"))
        touched_days.add(day)

    for row in optional.get("daily_cardiovascular_age", []):
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.vascular_age_years = _as_float(row.get("vascular_age"))
        metric.pulse_wave_velocity_m_s = _as_float(row.get("pulse_wave_velocity"))
        touched_days.add(day)

    for row in optional.get("vO2_max", []):
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.vo2_max = _as_float(row.get("vo2_max"))
        touched_days.add(day)

    for row in optional.get("sleep_time", []):
        day = _day_from_row(row)
        if not day:
            continue
        metric = _metric(db, user_id, day)
        metric.sleep_time_recommendation = (
            str(row["recommendation"]) if row.get("recommendation") is not None else None
        )
        metric.sleep_time_status = str(row["status"]) if row.get("status") is not None else None
        optimal_bedtime = row.get("optimal_bedtime")
        if isinstance(optimal_bedtime, dict):
            metric.optimal_bedtime_start_offset_seconds = _as_int(optimal_bedtime.get("start_offset"))
            metric.optimal_bedtime_end_offset_seconds = _as_int(optimal_bedtime.get("end_offset"))
            metric.optimal_bedtime_timezone_offset_seconds = _as_int(optimal_bedtime.get("day_tz"))
            _set_detail(metric, "optimal_bedtime", optimal_bedtime)
        touched_days.add(day)

    for row in optional.get("rest_mode_period", []):
        start_day = row.get("start_day")
        end_day = row.get("end_day") or sync_end.isoformat()
        try:
            period_start = max(date.fromisoformat(str(start_day)), sync_start)
            period_end = min(date.fromisoformat(str(end_day)), sync_end)
        except ValueError:
            continue
        current_day = period_start
        while current_day <= period_end:
            day = current_day.isoformat()
            metric = _metric(db, user_id, day)
            metric.rest_mode = True
            _set_detail(
                metric,
                "rest_mode_period",
                {
                    key: row.get(key)
                    for key in ("start_day", "end_day", "start_time", "end_time", "episodes")
                    if row.get(key) is not None
                },
            )
            touched_days.add(day)
            current_day += timedelta(days=1)

    sessions_by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in optional.get("session", []):
        day = _day_from_row(row)
        if day:
            sessions_by_day[day].append(_compact_session(row))
    for day, items in sessions_by_day.items():
        metric = _metric(db, user_id, day)
        _set_detail(metric, "sessions", items[:12])
        touched_days.add(day)

    tags_by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in optional.get("tag", []):
        day = _day_from_row(row)
        if day:
            tags_by_day[day].append(_compact_tag(row))
    for day, items in tags_by_day.items():
        metric = _metric(db, user_id, day)
        _set_detail(metric, "tags", items[:20])
        touched_days.add(day)

    if "heartrate" in granted_scopes:
        heart_rate_start = max(sync_start, sync_end - timedelta(days=HEART_RATE_INITIAL_DAYS - 1))
        try:
            heart_rows = active_client.fetch_timeseries(
                access_token,
                "heartrate",
                start_date=heart_rate_start,
                end_date=sync_end,
            )
        except OuraAPIError as exc:
            heart_rows = []
            warnings.append(f"heartrate: {exc}")

        heart_by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in heart_rows:
            day = _day_from_row(row)
            bpm = _as_float(row.get("bpm"))
            if day and bpm is not None:
                heart_by_day[day].append(row)
        for day, items in heart_by_day.items():
            bpms = [_as_float(item.get("bpm")) for item in items]
            values = [value for value in bpms if value is not None]
            if not values:
                continue
            metric = _metric(db, user_id, day)
            metric.heart_rate_average_bpm = round(sum(values) / len(values), 1)
            metric.heart_rate_min_bpm = min(values)
            metric.heart_rate_max_bpm = max(values)
            metric.heart_rate_samples = len(values)
            source_counts = Counter(str(item.get("source")) for item in items if item.get("source"))
            _set_detail(metric, "heart_rate_sources", dict(source_counts))
            touched_days.add(day)

    connection.last_sync_at = datetime.now(timezone.utc)
    connection.updated_at = connection.last_sync_at
    db.commit()

    from .adaptive_targets import refresh_adaptive_target

    refresh_adaptive_target(db, user_id, today=today)

    return {
        "synced_days": len(touched_days),
        "start_date": sync_start.isoformat(),
        "end_date": sync_end.isoformat(),
        "last_sync_at": connection.last_sync_at,
        "warnings": warnings,
        "missing_scopes": missing_oura_scopes(connection),
    }
