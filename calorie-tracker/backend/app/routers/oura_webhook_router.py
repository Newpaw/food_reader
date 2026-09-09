from __future__ import annotations

import hmac
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from .. import models
from ..deps import get_current_user
from ..oura_webhook_service import (
    OuraWebhookError,
    desired_webhook_pairs,
    list_webhook_subscriptions,
    oura_webhook_callback_url,
    oura_webhook_verification_token,
    oura_webhooks_ready,
    process_oura_webhook_event,
    reconcile_webhook_subscriptions,
    verify_webhook_signature,
)


router = APIRouter(prefix="/oura/webhook", tags=["oura"])


@router.get("", include_in_schema=False)
def verify_webhook(
    verification_token: str = Query(...),
    challenge: str = Query(...),
):
    expected = oura_webhook_verification_token()
    if not hmac.compare_digest(verification_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification token")
    return {"challenge": challenge}


@router.post("", include_in_schema=False)
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload must be an object")

    if not verify_webhook_signature(
        raw_body,
        payload,
        signature=request.headers.get("x-oura-signature"),
        timestamp=request.headers.get("x-oura-timestamp"),
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Oura webhook signature")

    event_type = str(payload.get("event_type") or "")
    data_type = str(payload.get("data_type") or "")
    if not event_type or not data_type:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing event_type or data_type")

    # Acknowledge immediately; the heavier API refresh runs after the response.
    background_tasks.add_task(process_oura_webhook_event, payload)
    return {"status": "accepted"}


@router.get("/status")
def webhook_status(current_user: models.User = Depends(get_current_user)) -> dict[str, Any]:
    del current_user  # authentication gate only
    response: dict[str, Any] = {
        "ready": oura_webhooks_ready(),
        "callback_url": oura_webhook_callback_url(),
        "desired": [
            {"data_type": data_type, "event_type": event_type}
            for data_type, event_type in desired_webhook_pairs()
        ],
    }
    if not oura_webhooks_ready():
        response["subscriptions"] = []
        return response
    try:
        response["subscriptions"] = list_webhook_subscriptions()
    except OuraWebhookError as exc:
        response["error"] = str(exc)
        response["subscriptions"] = []
    return response


@router.post("/reconcile")
def reconcile_webhooks(current_user: models.User = Depends(get_current_user)) -> dict[str, Any]:
    del current_user  # authentication gate only
    try:
        return reconcile_webhook_subscriptions()
    except OuraWebhookError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
