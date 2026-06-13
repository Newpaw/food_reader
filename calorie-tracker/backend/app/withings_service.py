import base64
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .settings import settings


WITHINGS_AUTH_URL = "https://account.withings.com/oauth2_user/authorize2"
WITHINGS_TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
WITHINGS_MEASURE_URL = "https://wbsapi.withings.net/measure"
WITHINGS_SCOPE = "user.metrics"
WITHINGS_MEASURE_TYPES = "1,5,6,8,76,77,88,170,226,227"
INITIAL_SYNC_DAYS = 365

MEASURE_TYPE_FIELDS = {
    1: "weight_kg",
    5: "fat_free_mass_kg",
    6: "fat_ratio",
    8: "fat_mass_kg",
    76: "muscle_mass_kg",
    77: "hydration_kg",
    88: "bone_mass_kg",
    170: "visceral_fat",
    226: "bmr",
    227: "metabolic_age",
}


class WithingsConfigError(RuntimeError):
    pass


class WithingsAPIError(RuntimeError):
    pass


def withings_configured() -> bool:
    return all([settings.WITHINGS_CLIENT_ID, settings.WITHINGS_CLIENT_SECRET, settings.WITHINGS_REDIRECT_URI])


def ensure_withings_configured() -> None:
    if not withings_configured():
        raise WithingsConfigError("Withings integration is not configured.")


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def build_oauth_state(user_id: int, expires_in_seconds: int = 600) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + expires_in_seconds,
        "type": "withings_oauth",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_oauth_state(state: str) -> int:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.PyJWTError as exc:
        raise WithingsAPIError("Invalid or expired Withings authorization state.") from exc

    if payload.get("type") != "withings_oauth" or not payload.get("sub"):
        raise WithingsAPIError("Invalid Withings authorization state.")
    return int(payload["sub"])


def build_authorization_url(user_id: int) -> str:
    ensure_withings_configured()
    params = {
        "response_type": "code",
        "client_id": settings.WITHINGS_CLIENT_ID,
        "state": build_oauth_state(user_id),
        "scope": WITHINGS_SCOPE,
        "redirect_uri": settings.WITHINGS_REDIRECT_URI,
    }
    return f"{WITHINGS_AUTH_URL}?{urlencode(params)}"


def _utc_from_timestamp(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _real_measure_value(measure: dict[str, Any]) -> float:
    return float(measure["value"]) * (10 ** int(measure.get("unit", 0)))


def _extract_token_body(response_data: dict[str, Any]) -> dict[str, Any]:
    if response_data.get("status", 0) != 0:
        raise WithingsAPIError(f"Withings API returned status {response_data.get('status')}.")
    body = response_data.get("body") or response_data
    if not body.get("access_token") or not body.get("refresh_token"):
        raise WithingsAPIError("Withings token response did not include required tokens.")
    return body


def _extract_measure_body(response_data: dict[str, Any]) -> dict[str, Any]:
    if response_data.get("status", 0) != 0:
        raise WithingsAPIError(f"Withings API returned status {response_data.get('status')}.")
    body = response_data.get("body") or {}
    if "measuregrps" not in body:
        raise WithingsAPIError("Withings measure response did not include measure groups.")
    return body


class WithingsClient:
    def _post_form(
        self,
        url: str,
        data: dict[str, Any],
        *,
        access_token: str | None = None,
        timeout: int = 20,
    ) -> dict[str, Any]:
        encoded = urlencode({key: value for key, value in data.items() if value is not None}).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        request = Request(url, data=encoded, headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def exchange_code(self, code: str) -> dict[str, Any]:
        ensure_withings_configured()
        data = self._post_form(
            WITHINGS_TOKEN_URL,
            {
                "action": "requesttoken",
                "client_id": settings.WITHINGS_CLIENT_ID,
                "client_secret": settings.WITHINGS_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.WITHINGS_REDIRECT_URI,
            },
        )
        return _extract_token_body(data)

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        ensure_withings_configured()
        data = self._post_form(
            WITHINGS_TOKEN_URL,
            {
                "action": "requesttoken",
                "client_id": settings.WITHINGS_CLIENT_ID,
                "client_secret": settings.WITHINGS_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return _extract_token_body(data)

    def get_measure_groups(
        self,
        access_token: str,
        *,
        startdate: int | None = None,
        enddate: int | None = None,
        lastupdate: int | None = None,
    ) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []
        offset = None
        while True:
            data = self._post_form(
                WITHINGS_MEASURE_URL,
                {
                    "action": "getmeas",
                    "meastypes": WITHINGS_MEASURE_TYPES,
                    "category": 1,
                    "startdate": startdate,
                    "enddate": enddate,
                    "lastupdate": lastupdate,
                    "offset": offset,
                },
                access_token=access_token,
            )
            body = _extract_measure_body(data)
            groups.extend(body.get("measuregrps", []))
            if not body.get("more"):
                break
            offset = body.get("offset")
            if offset is None:
                break
        return groups


def _store_connection_tokens(
    connection: models.WithingsConnection,
    token_body: dict[str, Any],
) -> None:
    connection.withings_user_id = str(token_body.get("userid") or token_body.get("user_id") or "")
    connection.access_token_encrypted = encrypt_token(token_body["access_token"])
    connection.refresh_token_encrypted = encrypt_token(token_body["refresh_token"])
    connection.scope = token_body.get("scope")
    expires_in = int(token_body.get("expires_in") or 0)
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None
    connection.updated_at = datetime.now(timezone.utc)


def save_connection_from_code(
    db: Session,
    user_id: int,
    code: str,
    *,
    client: WithingsClient | None = None,
) -> models.WithingsConnection:
    token_body = (client or WithingsClient()).exchange_code(code)
    connection = db.query(models.WithingsConnection).filter(models.WithingsConnection.user_id == user_id).first()
    if connection is None:
        connection = models.WithingsConnection(
            user_id=user_id,
            access_token_encrypted=encrypt_token(token_body["access_token"]),
            refresh_token_encrypted=encrypt_token(token_body["refresh_token"]),
        )
        db.add(connection)
    _store_connection_tokens(connection, token_body)
    db.commit()
    db.refresh(connection)
    return connection


def get_valid_access_token(
    db: Session,
    connection: models.WithingsConnection,
    *,
    client: WithingsClient | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if connection.token_expires_at and connection.token_expires_at > now + timedelta(seconds=60):
        return decrypt_token(connection.access_token_encrypted)

    refresh_token = decrypt_token(connection.refresh_token_encrypted)
    token_body = (client or WithingsClient()).refresh_access_token(refresh_token)
    _store_connection_tokens(connection, token_body)
    db.commit()
    db.refresh(connection)
    return decrypt_token(connection.access_token_encrypted)


def measurement_values_from_group(group: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    for measure in group.get("measures", []):
        field = MEASURE_TYPE_FIELDS.get(int(measure.get("type", -1)))
        if field:
            values[field] = round(_real_measure_value(measure), 4)
    return values


def upsert_measure_group(db: Session, user_id: int, group: dict[str, Any]) -> models.WithingsMeasurement | None:
    values = measurement_values_from_group(group)
    if not values:
        return None

    grpid = str(group.get("grpid"))
    if not grpid:
        return None

    measurement = (
        db.query(models.WithingsMeasurement)
        .filter(
            models.WithingsMeasurement.user_id == user_id,
            models.WithingsMeasurement.withings_grpid == grpid,
        )
        .first()
    )
    if measurement is None:
        measurement = models.WithingsMeasurement(user_id=user_id, withings_grpid=grpid)
        db.add(measurement)

    measurement.measured_at = _utc_from_timestamp(group.get("date")) or datetime.now(timezone.utc)
    measurement.remote_created_at = _utc_from_timestamp(group.get("created"))
    measurement.remote_modified_at = _utc_from_timestamp(group.get("modified"))
    measurement.attrib = group.get("attrib")
    measurement.category = group.get("category")
    measurement.device_id = group.get("deviceid") or group.get("hash_deviceid")
    measurement.model = group.get("model")
    measurement.updated_at = datetime.now(timezone.utc)
    for field, value in values.items():
        setattr(measurement, field, value)

    return measurement


def latest_weight_measurement(db: Session, user_id: int) -> models.WithingsMeasurement | None:
    return (
        db.query(models.WithingsMeasurement)
        .filter(
            models.WithingsMeasurement.user_id == user_id,
            models.WithingsMeasurement.weight_kg.isnot(None),
        )
        .order_by(models.WithingsMeasurement.measured_at.desc())
        .first()
    )


def sync_measurements(
    db: Session,
    user_id: int,
    *,
    client: WithingsClient | None = None,
) -> schemas.WithingsSyncOut:
    connection = db.query(models.WithingsConnection).filter(models.WithingsConnection.user_id == user_id).first()
    if not connection:
        raise WithingsAPIError("Withings account is not connected.")

    active_client = client or WithingsClient()
    access_token = get_valid_access_token(db, connection, client=active_client)
    now = datetime.now(timezone.utc)
    if connection.last_update_timestamp:
        groups = active_client.get_measure_groups(access_token, lastupdate=connection.last_update_timestamp)
    else:
        startdate = int((now - timedelta(days=INITIAL_SYNC_DAYS)).timestamp())
        groups = active_client.get_measure_groups(access_token, startdate=startdate, enddate=int(now.timestamp()))

    synced_count = 0
    max_modified = connection.last_update_timestamp or 0
    for group in groups:
        if upsert_measure_group(db, user_id, group):
            synced_count += 1
        if group.get("modified"):
            max_modified = max(max_modified, int(group["modified"]))

    connection.last_sync_at = now
    connection.last_update_timestamp = max_modified or connection.last_update_timestamp
    connection.updated_at = now
    db.commit()

    latest = latest_weight_measurement(db, user_id)
    profile_weight_updated = False
    if latest and latest.weight_kg is not None:
        profile_weight_updated = crud.apply_withings_profile_weight(
            db,
            user_id,
            latest.weight_kg,
            latest.measured_at,
        ) is not None

    db.refresh(connection)
    return schemas.WithingsSyncOut(
        synced_count=synced_count,
        latest_weight_kg=latest.weight_kg if latest else None,
        latest_measured_at=latest.measured_at if latest else None,
        profile_weight_updated=profile_weight_updated,
        last_sync_at=connection.last_sync_at,
    )
