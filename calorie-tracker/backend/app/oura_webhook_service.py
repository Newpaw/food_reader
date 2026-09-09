from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from .database import SessionLocal
from .logger import get_logger
from .oura_models import OuraConnection
from .oura_service import OuraAPIError, sync_oura_data
from .settings import settings

logger = get_logger(__name__)

OURA_WEBHOOK_API = "https://api.ouraring.com/v2/webhook/subscription"
_ALLOWED_EVENT_TYPES = {"create", "update", "delete"}
_WEBHOOK_SYNC_DEBOUNCE_SECONDS = 20.0
_webhook_sync_guard = threading.Lock()
_last_webhook_sync_by_user: dict[int, float] = {}


class OuraWebhookError(RuntimeError):
    pass


def _csv_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def oura_webhook_callback_url() -> str:
    explicit = (settings.OURA_WEBHOOK_CALLBACK_URL or "").strip()
    if explicit:
        return explicit.rstrip("/")
    return f"{settings.mcp_public_base_url}/oura/webhook"


def oura_webhook_verification_token() -> str:
    explicit = (settings.OURA_WEBHOOK_VERIFICATION_TOKEN or "").strip()
    if explicit:
        return explicit
    # Stable, deployment-specific token without introducing another mandatory
    # production secret. It is only used for Oura's subscription challenge.
    return hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        b"food-reader-oura-webhook-verification",
        hashlib.sha256,
    ).hexdigest()


def desired_webhook_pairs() -> list[tuple[str, str]]:
    data_types = _csv_values(settings.OURA_WEBHOOK_DATA_TYPES)
    event_types = [
        value
        for value in _csv_values(settings.OURA_WEBHOOK_EVENT_TYPES)
        if value in _ALLOWED_EVENT_TYPES
    ]
    return [(data_type, event_type) for data_type in data_types for event_type in event_types]


def oura_webhooks_ready() -> bool:
    callback_url = oura_webhook_callback_url()
    return bool(
        settings.OURA_WEBHOOK_ENABLED
        and settings.OURA_CLIENT_ID
        and settings.OURA_CLIENT_SECRET
        and callback_url.startswith("https://")
    )


def _api_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    if not settings.OURA_CLIENT_ID or not settings.OURA_CLIENT_SECRET:
        raise OuraWebhookError("Oura client credentials are not configured.")

    headers = {
        "Accept": "application/json",
        "x-client-id": settings.OURA_CLIENT_ID,
        "x-client-secret": settings.OURA_CLIENT_SECRET,
    }
    body = None
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = (
                detail.get("detail")
                or detail.get("title")
                or detail.get("error_description")
                or detail.get("error")
            )
        except Exception:
            message = None
        raise OuraWebhookError(message or f"Oura webhook API returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise OuraWebhookError(f"Unable to reach Oura webhook API: {exc.reason}") from exc


def list_webhook_subscriptions() -> list[dict[str, Any]]:
    payload = _api_request(OURA_WEBHOOK_API)
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise OuraWebhookError("Unexpected Oura webhook subscription list response.")
    return [row for row in payload if isinstance(row, dict)]


def create_webhook_subscription(data_type: str, event_type: str) -> dict[str, Any]:
    payload = _api_request(
        OURA_WEBHOOK_API,
        method="POST",
        payload={
            "callback_url": oura_webhook_callback_url(),
            "verification_token": oura_webhook_verification_token(),
            "event_type": event_type,
            "data_type": data_type,
        },
    )
    return payload if isinstance(payload, dict) else {}


def update_webhook_subscription(subscription_id: str, data_type: str, event_type: str) -> dict[str, Any]:
    payload = _api_request(
        f"{OURA_WEBHOOK_API}/{subscription_id}",
        method="PUT",
        payload={
            "callback_url": oura_webhook_callback_url(),
            "verification_token": oura_webhook_verification_token(),
            "event_type": event_type,
            "data_type": data_type,
        },
    )
    return payload if isinstance(payload, dict) else {}


def renew_webhook_subscription(subscription_id: str) -> dict[str, Any]:
    payload = _api_request(
        f"{OURA_WEBHOOK_API}/renew/{subscription_id}",
        method="PUT",
    )
    return payload if isinstance(payload, dict) else {}


def _parse_expiration(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def reconcile_webhook_subscriptions() -> dict[str, Any]:
    """Create missing subscriptions, repair callback changes and renew expiring ones."""

    if not oura_webhooks_ready():
        return {
            "enabled": False,
            "reason": "Oura webhooks require enabled client credentials and a public HTTPS callback URL.",
            "callback_url": oura_webhook_callback_url(),
        }

    callback_url = oura_webhook_callback_url()
    existing = list_webhook_subscriptions()
    now = datetime.now(timezone.utc)
    renew_before = now + timedelta(days=max(1, settings.OURA_WEBHOOK_RENEW_DAYS))
    created = 0
    updated = 0
    renewed = 0
    unchanged = 0
    errors: list[str] = []

    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in existing:
        pair = (str(row.get("data_type") or ""), str(row.get("event_type") or ""))
        by_pair.setdefault(pair, []).append(row)

    for data_type, event_type in desired_webhook_pairs():
        candidates = by_pair.get((data_type, event_type), [])
        exact = next((row for row in candidates if row.get("callback_url") == callback_url), None)
        selected = exact or (candidates[0] if candidates else None)
        try:
            if selected is None:
                create_webhook_subscription(data_type, event_type)
                created += 1
                continue

            subscription_id = str(selected.get("id") or "")
            if not subscription_id:
                raise OuraWebhookError(f"Subscription {data_type}/{event_type} has no id.")

            if selected.get("callback_url") != callback_url:
                selected = update_webhook_subscription(subscription_id, data_type, event_type)
                updated += 1

            expiration = _parse_expiration(selected.get("expiration_time"))
            if expiration is None or expiration <= renew_before:
                renew_webhook_subscription(subscription_id)
                renewed += 1
            else:
                unchanged += 1
        except OuraWebhookError as exc:
            errors.append(f"{data_type}/{event_type}: {exc}")

    result = {
        "enabled": True,
        "callback_url": callback_url,
        "desired_subscriptions": len(desired_webhook_pairs()),
        "existing_subscriptions": len(existing),
        "created": created,
        "updated": updated,
        "renewed": renewed,
        "unchanged": unchanged,
        "errors": errors,
    }
    if errors:
        logger.warning("Oura webhook reconciliation completed with errors: %s", errors)
    else:
        logger.info("Oura webhook reconciliation completed: %s", result)
    return result


def verify_webhook_signature(
    raw_body: bytes,
    payload: dict[str, Any],
    *,
    signature: str | None,
    timestamp: str | None,
) -> bool:
    """Verify Oura's HMAC-SHA256 callback signature.

    Oura documents the signature as HMAC(client_secret, timestamp + JSON body).
    Accept both the exact wire body and a compact JSON serialization to match
    common framework JSON parsers while keeping comparison constant-time.
    """

    if not settings.OURA_CLIENT_SECRET or not signature or not timestamp:
        return False

    secret = settings.OURA_CLIENT_SECRET.encode("utf-8")
    candidates = [raw_body]
    compact = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if compact != raw_body:
        candidates.append(compact)

    provided = signature.strip().upper()
    for body in candidates:
        expected = hmac.new(secret, timestamp.encode("utf-8") + body, hashlib.sha256).hexdigest().upper()
        if hmac.compare_digest(expected, provided):
            return True
    return False


def _find_connection_for_oura_user(db: Session, oura_user_id: str) -> OuraConnection | None:
    connection = (
        db.query(OuraConnection)
        .filter(OuraConnection.oura_user_id == oura_user_id)
        .first()
    )
    if connection is not None:
        return connection

    # Migration convenience for a personal/single-user deployment created
    # before oura_user_id was persisted. Never guess when multiple accounts exist.
    all_connections = db.query(OuraConnection).all()
    if len(all_connections) == 1 and not all_connections[0].oura_user_id:
        all_connections[0].oura_user_id = oura_user_id
        db.commit()
        db.refresh(all_connections[0])
        return all_connections[0]
    return None


def _claim_webhook_sync(user_id: int) -> bool:
    """Coalesce a burst of Oura notifications into one incremental refresh."""

    now = time.monotonic()
    with _webhook_sync_guard:
        previous = _last_webhook_sync_by_user.get(user_id)
        if previous is not None and now - previous < _WEBHOOK_SYNC_DEBOUNCE_SECONDS:
            return False
        _last_webhook_sync_by_user[user_id] = now
        return True


def process_oura_webhook_event(payload: dict[str, Any]) -> None:
    """Refresh the local Oura cache after a verified create/update notification."""

    oura_user_id = str(payload.get("user_id") or "").strip()
    if not oura_user_id:
        logger.warning("Ignoring Oura webhook without user_id: %s", payload)
        return

    db = SessionLocal()
    try:
        connection = _find_connection_for_oura_user(db, oura_user_id)
        if connection is None:
            logger.info("Ignoring Oura webhook for an unlinked user_id=%s", oura_user_id)
            return
        if not _claim_webhook_sync(connection.user_id):
            logger.info(
                "Coalesced Oura webhook user=%s event=%s/%s object=%s",
                connection.user_id,
                payload.get("data_type"),
                payload.get("event_type"),
                payload.get("object_id"),
            )
            return
        try:
            result = sync_oura_data(db, connection.user_id)
            logger.info(
                "Oura webhook synced Food Reader user=%s event=%s/%s object=%s result=%s",
                connection.user_id,
                payload.get("data_type"),
                payload.get("event_type"),
                payload.get("object_id"),
                result,
            )
        except OuraAPIError as exc:
            logger.warning("Oura webhook sync failed for user=%s: %s", connection.user_id, exc)
    finally:
        db.close()


async def run_oura_webhook_reconciler() -> None:
    """Best-effort subscription maintenance for the long-running API process."""

    await asyncio.sleep(max(0, settings.OURA_WEBHOOK_STARTUP_DELAY_SECONDS))
    while True:
        if oura_webhooks_ready():
            try:
                await asyncio.to_thread(reconcile_webhook_subscriptions)
            except Exception:
                logger.exception("Unexpected Oura webhook reconciliation failure")
        await asyncio.sleep(max(1, settings.OURA_WEBHOOK_RECONCILE_HOURS) * 3600)
