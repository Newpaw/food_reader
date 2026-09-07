import html
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator, Literal
from urllib.parse import urlparse

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from . import crud, database, mcp_oauth, models, schemas
from .assistant_service import execute_tool
from .oura_models import OuraConnection, OuraDailyMetric
from .oura_service import (
    OuraAPIError,
    OuraConfigError,
    build_authorization_url as build_oura_authorization_url,
    missing_oura_scopes,
    oura_configured,
    sync_oura_data,
)
from .routers.meals_router import (
    create_text_meal as create_text_meal_route,
    delete_meal as delete_meal_route,
    reanalyze_meal as reanalyze_meal_route,
    update_meal as update_meal_route,
)
from .settings import settings
from .withings_service import (
    WithingsAPIError,
    WithingsConfigError,
    build_authorization_url as build_withings_authorization_url,
    latest_weight_measurement,
    sync_measurements,
    withings_configured,
)

# Keep the original list object because main.py imports it before this module.
# Mutating it upgrades OAuth discovery/provider configuration everywhere.
MCP_SCOPES = mcp_oauth.MCP_SCOPES
MCP_SCOPES[:] = [
    "profile:read",
    "profile:write",
    "meals:read",
    "meals:write",
    "health:read",
    "health:write",
]
mcp_oauth.SCOPE_LABELS.clear()
mcp_oauth.SCOPE_LABELS.update(
    {
        "profile:read": "Číst profil a nutriční cíle",
        "profile:write": "Měnit profil a nutriční cíle",
        "meals:read": "Číst jídla a nutriční historii",
        "meals:write": "Přidávat, měnit a mazat jídla",
        "health:read": "Číst Oura, Withings a zdravotní souhrny",
        "health:write": "Synchronizovat a spravovat Oura a Withings",
    }
)
oauth_provider = mcp_oauth.oauth_provider

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
EXTERNAL_READ = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
CREATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)
UPDATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
SYNC = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)


def _oauth_meta(*scopes: str) -> dict[str, Any]:
    return {"securitySchemes": [{"type": "oauth2", "scopes": list(scopes)}]}


PROFILE_READ_META = _oauth_meta("profile:read")
PROFILE_WRITE_META = _oauth_meta("profile:write")
MEALS_READ_META = _oauth_meta("meals:read")
MEALS_WRITE_META = _oauth_meta("meals:write")
HEALTH_READ_META = _oauth_meta("health:read")
HEALTH_WRITE_META = _oauth_meta("health:write")
ALL_READ_META = _oauth_meta("profile:read", "meals:read", "health:read")


def _full_access_consent_page(
    request_token: str,
    payload: dict[str, Any],
    error: str | None = None,
) -> HTMLResponse:
    client_name = html.escape(str(payload.get("client_name") or "Externí agent"))
    scope_items = "".join(
        f"<li>{html.escape(mcp_oauth.SCOPE_LABELS.get(scope, scope))}</li>"
        for scope in payload.get("scopes", [])
    )
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    escaped_request = html.escape(request_token, quote=True)
    body = f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Připojit Food Reader</title><style>
body{{font-family:system-ui,sans-serif;background:#f5f7f6;color:#17201b;margin:0;padding:32px 16px}}
main{{max-width:560px;margin:auto;background:white;padding:28px;border-radius:18px;box-shadow:0 12px 40px #0001}}
h1{{font-size:1.55rem;margin-top:0}}label{{display:block;font-weight:600;margin-top:16px}}
input{{box-sizing:border-box;width:100%;padding:12px;margin-top:6px;border:1px solid #aeb8b1;border-radius:9px;font:inherit}}
.actions{{display:flex;gap:10px;margin-top:24px}}button{{padding:12px 18px;border:0;border-radius:9px;font:inherit;font-weight:700;cursor:pointer}}
.approve{{background:#176b45;color:white}}.deny{{background:#e7ebe8;color:#26352c}}.error{{color:#a11b1b;font-weight:600}}
.warning{{padding:12px;border-radius:9px;background:#fff4df;color:#704b00}}small{{color:#56645b}}li{{margin:7px 0}}
</style></head><body><main><h1>Připojit {client_name} k Food Readeru</h1>
<p>Po přihlášení bude agent moci podle udělených oprávnění:</p><ul>{scope_items}</ul>
<p class="warning"><strong>Plný přístup:</strong> zapisovací oprávnění umožňují agentovi měnit a mazat data a spouštět synchronizace. Přístup je vždy svázán s tímto přihlášeným Food Reader účtem.</p>
<p><small>Přístup lze kdykoli odvolat zrušením OAuth tokenu.</small></p>{error_html}
<form method="post" action="/oauth/consent" autocomplete="on">
<input type="hidden" name="request_token" value="{escaped_request}">
<label for="email">E-mail</label><input id="email" name="email" type="email" autocomplete="username" required>
<label for="password">Heslo</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<div class="actions"><button class="approve" name="action" value="approve" type="submit">Povolit přístup</button>
<button class="deny" name="action" value="deny" type="submit" formnovalidate>Zamítnout</button></div></form>
</main></body></html>"""
    # Deliberately omit CSP/form-action restrictions. OAuth clients may use any
    # validated HTTPS redirect URI registered through DCR.
    return HTMLResponse(
        body,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


# show_consent()/submit_consent() resolve this module global at request time,
# so replacing it here also updates the functions already imported by main.py.
mcp_oauth._consent_page = _full_access_consent_page


def _transport_security() -> TransportSecuritySettings:
    parsed = urlparse(settings.mcp_public_base_url)
    public_host = parsed.netloc
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            public_host,
            "testserver",
            "localhost:*",
            "127.0.0.1:*",
            "[::1]:*",
        ],
        allowed_origins=[
            settings.mcp_public_base_url,
            "http://localhost:*",
            "http://127.0.0.1:*",
            "http://[::1]:*",
        ],
    )


mcp = FastMCP(
    "Food Reader",
    instructions=(
        "Read and manage the authenticated user's Food Reader nutrition, profile and wearable data. "
        "Write tools may create or update data. Tools marked destructive can delete data or disconnect "
        "a wearable account and should only be used when the user explicitly asks for that destructive action. "
        "Never expose credentials or tokens, and never present wearable estimates as a diagnosis."
    ),
    website_url=settings.mcp_public_base_url,
    auth_server_provider=oauth_provider,
    auth=AuthSettings(
        issuer_url=settings.mcp_public_base_url,
        resource_server_url=settings.mcp_resource_url,
        # Authenticate every MCP request, but do not require the union of every
        # possible tool scope at the transport layer. This keeps tools/list
        # usable with an older read-only token so clients can discover new
        # write tools and initiate a scope upgrade. Each tool enforces its own
        # scopes below.
        required_scopes=None,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=MCP_SCOPES,
            default_scopes=MCP_SCOPES,
        ),
        revocation_options=RevocationOptions(enabled=True),
    ),
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    transport_security=_transport_security(),
)


def _authenticated_user_id(*required_scopes: str) -> int:
    token = get_access_token()
    if token is None or not token.subject:
        raise ValueError("Authenticated Food Reader user is missing")

    granted = set(token.scopes or [])
    missing = [scope for scope in required_scopes if scope not in granted]
    if missing:
        raise ValueError(
            "OAuth token is missing required scope(s): "
            + ", ".join(missing)
            + ". Reconnect Food Reader in ChatGPT to grant the new permissions."
        )

    try:
        return int(token.subject)
    except ValueError as exc:
        raise ValueError("Authenticated Food Reader user is invalid") from exc


@contextmanager
def _session_user(*required_scopes: str) -> Iterator[tuple[Any, models.User]]:
    user_id = _authenticated_user_id(*required_scopes)
    with database.SessionLocal() as db:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            raise ValueError("Food Reader user no longer exists")
        yield db, user


def _tool_error(exc: Exception) -> ValueError:
    if isinstance(exc, HTTPException):
        return ValueError(str(exc.detail))
    return ValueError(str(exc))


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise ValueError("Unexpected Food Reader response")


def _parse_date(value: str | None, field_name: str) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD") from exc


def _execute(
    tool_name: str,
    args: dict[str, Any],
    *,
    required_scopes: tuple[str, ...],
    timezone_name: str = "UTC",
    locale: str = "cs",
) -> dict[str, Any]:
    with _session_user(*required_scopes) as (db, user):
        result = execute_tool(
            db,
            user,
            tool_name,
            args,
            timezone_name=timezone_name,
            locale=locale,
        )
        if "error" in result:
            raise ValueError(str(result["error"]))
        return result


@mcp.tool(
    title="Food Reader data inventory",
    description="List connected sources and date coverage for this user's Food Reader data.",
    annotations=READ_ONLY,
    meta=ALL_READ_META,
)
def get_data_inventory() -> dict[str, Any]:
    return _execute(
        "get_data_inventory",
        {},
        required_scopes=("profile:read", "meals:read", "health:read"),
    )


@mcp.tool(
    title="Food Reader profile",
    description="Read the user's profile, body data and current nutrition targets.",
    annotations=READ_ONLY,
    meta=PROFILE_READ_META,
)
def get_profile(timezone_name: str = "UTC") -> dict[str, Any]:
    return _execute(
        "get_profile",
        {},
        required_scopes=("profile:read",),
        timezone_name=timezone_name,
    )


@mcp.tool(
    title="Food Reader meals",
    description="Read meals and nutrition history with optional local date filters and pagination.",
    annotations=READ_ONLY,
    meta=MEALS_READ_META,
)
def get_meals(
    start_date: str | None = None,
    end_date: str | None = None,
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] | None = None,
    limit: int = 50,
    offset: int = 0,
    timezone_name: str = "UTC",
) -> dict[str, Any]:
    return _execute(
        "get_meals",
        {
            "start_date": start_date,
            "end_date": end_date,
            "meal_type": meal_type,
            "limit": limit,
            "offset": offset,
        },
        required_scopes=("meals:read",),
        timezone_name=timezone_name,
    )


@mcp.tool(
    title="Create Food Reader meal",
    description=(
        "Create a meal from a text description. Nutrition fields are optional; when omitted, "
        "Food Reader AI analyzes the description. Provide all nutrition values and consumed_at "
        "to create a fully manual record without AI inference."
    ),
    annotations=CREATE,
    meta=MEALS_WRITE_META,
)
async def create_text_meal(meal: schemas.TextMealCreate) -> dict[str, Any]:
    with _session_user("meals:write") as (db, user):
        try:
            result = await create_text_meal_route(meal, db=db, user=user)
            return _model_dump(result)
        except Exception as exc:
            raise _tool_error(exc) from exc


@mcp.tool(
    title="Update Food Reader meal",
    description=(
        "Update selected fields of one meal owned by the authenticated user. Supported fields include "
        "calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, consumed_at and notes."
    ),
    annotations=UPDATE,
    meta=MEALS_WRITE_META,
)
def update_meal(meal_id: int, changes: schemas.MealUpdate) -> dict[str, Any]:
    with _session_user("meals:write") as (db, user):
        try:
            result = update_meal_route(meal_id, changes, db=db, user=user)
            return _model_dump(result)
        except Exception as exc:
            raise _tool_error(exc) from exc


@mcp.tool(
    title="Reanalyze Food Reader meal photo",
    description=(
        "Re-run AI analysis for an existing photo meal using a clarification or correction. "
        "This is only available for meals that still have their source image."
    ),
    annotations=UPDATE,
    meta=MEALS_WRITE_META,
)
async def reanalyze_meal(
    meal_id: int,
    refinement_context: str,
) -> dict[str, Any]:
    payload = schemas.MealReanalysis(refinement_context=refinement_context)
    with _session_user("meals:write") as (db, user):
        try:
            result = await reanalyze_meal_route(meal_id, payload, db=db, user=user)
            return _model_dump(result)
        except Exception as exc:
            raise _tool_error(exc) from exc


@mcp.tool(
    title="Delete Food Reader meal",
    description="Permanently delete one meal owned by the authenticated user, including its stored image when present.",
    annotations=DESTRUCTIVE,
    meta=MEALS_WRITE_META,
)
def delete_meal(meal_id: int) -> dict[str, Any]:
    with _session_user("meals:write") as (db, user):
        try:
            delete_meal_route(meal_id, db=db, user=user)
            return {"deleted": True, "meal_id": meal_id}
        except Exception as exc:
            raise _tool_error(exc) from exc


@mcp.tool(
    title="Create or update Food Reader profile",
    description=(
        "Create the profile if it does not exist, otherwise update selected profile fields. "
        "Controls height, weight, age, gender, activity level, goal, dietary preference, custom macro/calorie targets, "
        "and adaptive Oura-based calorie targets."
    ),
    annotations=UPDATE,
    meta=PROFILE_WRITE_META,
)
def upsert_profile(
    profile: schemas.UserProfileUpdate,
    timezone_name: str = "UTC",
) -> dict[str, Any]:
    with _session_user("profile:write") as (db, user):
        try:
            existing = crud.get_user_profile(db, user.id)
            if existing is None:
                create_payload = schemas.UserProfileCreate.model_validate(
                    profile.model_dump(exclude_unset=True)
                )
                crud.create_user_profile(db, user.id, create_payload)
            else:
                updated = crud.update_user_profile(db, user.id, profile)
                if updated is None:
                    raise ValueError("Profile could not be updated")
            result = execute_tool(
                db,
                user,
                "get_profile",
                {},
                timezone_name=timezone_name,
                locale="cs",
            )
            if "error" in result:
                raise ValueError(str(result["error"]))
            return result
        except Exception as exc:
            raise _tool_error(exc) from exc


@mcp.tool(
    title="Delete Food Reader profile",
    description=(
        "Permanently delete the authenticated user's Food Reader profile and nutrition target configuration. "
        "This does not delete the user account or meal history."
    ),
    annotations=DESTRUCTIVE,
    meta=PROFILE_WRITE_META,
)
def delete_profile() -> dict[str, Any]:
    with _session_user("profile:write") as (db, user):
        if not crud.delete_user_profile(db, user.id):
            raise ValueError("Profile not found")
        return {"deleted": True}


@mcp.tool(
    title="Withings measurements",
    description="Read the user's weight and body-composition measurements from Withings.",
    annotations=READ_ONLY,
    meta=HEALTH_READ_META,
)
def get_withings_measurements(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
    timezone_name: str = "UTC",
) -> dict[str, Any]:
    return _execute(
        "get_withings_measurements",
        {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        },
        required_scopes=("health:read",),
        timezone_name=timezone_name,
    )


@mcp.tool(
    title="Withings connection status",
    description="Read Withings connection status, last synchronization and latest measured weight.",
    annotations=READ_ONLY,
    meta=HEALTH_READ_META,
)
def get_withings_status() -> dict[str, Any]:
    with _session_user("health:read") as (db, user):
        connection = (
            db.query(models.WithingsConnection)
            .filter(models.WithingsConnection.user_id == user.id)
            .first()
        )
        latest = latest_weight_measurement(db, user.id)
        return {
            "configured": withings_configured(),
            "connected": connection is not None,
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection and connection.last_sync_at
            else None,
            "latest_weight_kg": latest.weight_kg if latest else None,
            "latest_measured_at": latest.measured_at.isoformat()
            if latest and latest.measured_at
            else None,
            "scope": connection.scope if connection else None,
        }


@mcp.tool(
    title="Connect Withings",
    description="Generate the user-specific Withings OAuth authorization URL. Open the returned URL in a browser to connect the account.",
    annotations=EXTERNAL_READ,
    meta=HEALTH_WRITE_META,
)
def get_withings_connect_url() -> dict[str, Any]:
    user_id = _authenticated_user_id("health:write")
    try:
        return {"authorization_url": build_withings_authorization_url(user_id)}
    except (WithingsConfigError, WithingsAPIError) as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool(
    title="Synchronize Withings",
    description="Fetch the latest Withings measurements into Food Reader and refresh profile weight when applicable.",
    annotations=SYNC,
    meta=HEALTH_WRITE_META,
)
def sync_withings() -> dict[str, Any]:
    with _session_user("health:write") as (db, user):
        try:
            return _model_dump(sync_measurements(db, user.id))
        except (WithingsConfigError, WithingsAPIError) as exc:
            raise ValueError(str(exc)) from exc


@mcp.tool(
    title="Disconnect Withings",
    description="Disconnect Withings and permanently remove synchronized Withings measurements from Food Reader.",
    annotations=DESTRUCTIVE,
    meta=HEALTH_WRITE_META,
)
def disconnect_withings() -> dict[str, Any]:
    with _session_user("health:write") as (db, user):
        deleted_measurements = (
            db.query(models.WithingsMeasurement)
            .filter(models.WithingsMeasurement.user_id == user.id)
            .delete()
        )
        connection = (
            db.query(models.WithingsConnection)
            .filter(models.WithingsConnection.user_id == user.id)
            .first()
        )
        if connection:
            db.delete(connection)
        db.commit()
        return {
            "disconnected": True,
            "deleted_measurements": int(deleted_measurements or 0),
        }


@mcp.tool(
    title="Oura daily data",
    description=(
        "Read rich daily Oura activity, readiness, sleep, heart-rate, stress, recovery, "
        "SpO2, cardiovascular, workout, session, tag and rest-mode data."
    ),
    annotations=READ_ONLY,
    meta=HEALTH_READ_META,
)
def get_oura_daily(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    return _execute(
        "get_oura_daily",
        {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        },
        required_scopes=("health:read",),
    )


@mcp.tool(
    title="Oura connection status",
    description="Read Oura connection, granted scopes, sync state and latest daily metrics.",
    annotations=READ_ONLY,
    meta=HEALTH_READ_META,
)
def get_oura_status() -> dict[str, Any]:
    with _session_user("health:read") as (db, user):
        connection = (
            db.query(OuraConnection)
            .filter(OuraConnection.user_id == user.id)
            .first()
        )
        metric_count = (
            db.query(OuraDailyMetric)
            .filter(OuraDailyMetric.user_id == user.id)
            .count()
        )
        latest = (
            db.query(OuraDailyMetric)
            .filter(OuraDailyMetric.user_id == user.id)
            .order_by(OuraDailyMetric.day.desc())
            .first()
        )
        return {
            "configured": oura_configured(),
            "connected": connection is not None,
            "scope": connection.scope if connection else None,
            "missing_scopes": missing_oura_scopes(connection) if connection else [],
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection and connection.last_sync_at
            else None,
            "synced_days": metric_count,
            "latest_day": latest.day if latest else None,
            "latest_readiness": latest.readiness_score if latest else None,
            "latest_sleep_score": latest.sleep_score if latest else None,
            "latest_spo2": latest.spo2_average_percent if latest else None,
            "latest_resilience": latest.resilience_level if latest else None,
            "ring_battery": (
                {
                    "level_percent": connection.ring_battery_level_percent,
                    "charging": connection.ring_battery_charging,
                    "in_charger": connection.ring_battery_in_charger,
                    "updated_at": connection.ring_battery_updated_at.isoformat()
                    if connection.ring_battery_updated_at
                    else None,
                }
                if connection and connection.ring_battery_level_percent is not None
                else None
            ),
        }


@mcp.tool(
    title="Connect Oura",
    description="Generate the user-specific Oura OAuth authorization URL. Open the returned URL in a browser to connect or reauthorize Oura.",
    annotations=EXTERNAL_READ,
    meta=HEALTH_WRITE_META,
)
def get_oura_connect_url() -> dict[str, Any]:
    user_id = _authenticated_user_id("health:write")
    try:
        return {"authorization_url": build_oura_authorization_url(user_id)}
    except (OuraConfigError, OuraAPIError) as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool(
    title="Synchronize Oura",
    description=(
        "Fetch Oura data into Food Reader. Without dates this performs the normal incremental sync; "
        "start_date/end_date can force a YYYY-MM-DD range."
    ),
    annotations=SYNC,
    meta=HEALTH_WRITE_META,
)
def sync_oura(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if start and end and end < start:
        raise ValueError("end_date must be on or after start_date")
    with _session_user("health:write") as (db, user):
        try:
            return sync_oura_data(db, user.id, start_date=start, end_date=end)
        except (OuraConfigError, OuraAPIError) as exc:
            raise ValueError(str(exc)) from exc


@mcp.tool(
    title="Synchronize all wearables",
    description="Synchronize both Oura and Withings. Returns a per-source result so one unavailable source does not hide the other result.",
    annotations=SYNC,
    meta=HEALTH_WRITE_META,
)
def sync_all_wearables(
    oura_start_date: str | None = None,
    oura_end_date: str | None = None,
) -> dict[str, Any]:
    start = _parse_date(oura_start_date, "oura_start_date")
    end = _parse_date(oura_end_date, "oura_end_date")
    if start and end and end < start:
        raise ValueError("oura_end_date must be on or after oura_start_date")

    result: dict[str, Any] = {}
    with _session_user("health:write") as (db, user):
        try:
            result["oura"] = sync_oura_data(
                db,
                user.id,
                start_date=start,
                end_date=end,
            )
        except (OuraConfigError, OuraAPIError) as exc:
            result["oura"] = {"error": str(exc)}
        try:
            result["withings"] = _model_dump(sync_measurements(db, user.id))
        except (WithingsConfigError, WithingsAPIError) as exc:
            result["withings"] = {"error": str(exc)}
    return result


@mcp.tool(
    title="Disconnect Oura",
    description=(
        "Disconnect Oura, permanently remove synchronized Oura metrics from Food Reader, "
        "and disable adaptive Oura-based calorie targets."
    ),
    annotations=DESTRUCTIVE,
    meta=HEALTH_WRITE_META,
)
def disconnect_oura() -> dict[str, Any]:
    with _session_user("health:write") as (db, user):
        deleted_days = (
            db.query(OuraDailyMetric)
            .filter(OuraDailyMetric.user_id == user.id)
            .delete()
        )
        connection = (
            db.query(OuraConnection)
            .filter(OuraConnection.user_id == user.id)
            .first()
        )
        if connection:
            db.delete(connection)
        profile = crud.get_user_profile(db, user.id)
        if profile:
            profile.adaptive_calories_enabled = False
            profile.adaptive_target_calories = None
            profile.adaptive_target_updated_on = None
        db.commit()
        return {
            "disconnected": True,
            "deleted_days": int(deleted_days or 0),
            "adaptive_calories_disabled": profile is not None,
        }


@mcp.tool(
    title="Combined health summary",
    description=(
        "Combine Food Reader nutrition with Oura and Withings for a date range, including "
        "daily energy balance, recovery, targets, latest weight and non-causal correlations."
    ),
    annotations=READ_ONLY,
    meta=ALL_READ_META,
)
def get_health_summary(
    start_date: str,
    end_date: str,
    timezone_name: str = "UTC",
    locale: Literal["cs", "en"] = "cs",
) -> dict[str, Any]:
    return _execute(
        "get_health_summary",
        {"start_date": start_date, "end_date": end_date},
        required_scopes=("profile:read", "meals:read", "health:read"),
        timezone_name=timezone_name,
        locale=locale,
    )


mcp_http_app = mcp.streamable_http_app()
