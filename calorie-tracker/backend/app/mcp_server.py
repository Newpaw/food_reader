from typing import Any, Literal
from urllib.parse import urlparse

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from . import database, models
from .assistant_service import execute_tool
from .mcp_oauth import MCP_SCOPES, oauth_provider
from .settings import settings

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
OAUTH_META = {"securitySchemes": [{"type": "oauth2", "scopes": MCP_SCOPES}]}


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
        "Read the authenticated user's Food Reader nutrition and wearable data. "
        "All tools are read-only. Never present wearable estimates as a diagnosis."
    ),
    website_url=settings.mcp_public_base_url,
    auth_server_provider=oauth_provider,
    auth=AuthSettings(
        issuer_url=settings.mcp_public_base_url,
        resource_server_url=settings.mcp_resource_url,
        required_scopes=MCP_SCOPES,
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


def _execute(
    tool_name: str,
    args: dict[str, Any],
    *,
    timezone_name: str = "UTC",
    locale: str = "cs",
) -> dict[str, Any]:
    token = get_access_token()
    if token is None or not token.subject:
        raise ValueError("Authenticated Food Reader user is missing")
    try:
        user_id = int(token.subject)
    except ValueError as exc:
        raise ValueError("Authenticated Food Reader user is invalid") from exc

    with database.SessionLocal() as db:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            raise ValueError("Food Reader user no longer exists")
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
    meta=OAUTH_META,
)
def get_data_inventory() -> dict[str, Any]:
    return _execute("get_data_inventory", {})


@mcp.tool(
    title="Food Reader profile",
    description="Read the user's profile, body data and current nutrition targets.",
    annotations=READ_ONLY,
    meta=OAUTH_META,
)
def get_profile(timezone_name: str = "UTC") -> dict[str, Any]:
    return _execute("get_profile", {}, timezone_name=timezone_name)


@mcp.tool(
    title="Food Reader meals",
    description="Read meals and nutrition history with optional local date filters and pagination.",
    annotations=READ_ONLY,
    meta=OAUTH_META,
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
        timezone_name=timezone_name,
    )


@mcp.tool(
    title="Withings measurements",
    description="Read the user's weight and body-composition measurements from Withings.",
    annotations=READ_ONLY,
    meta=OAUTH_META,
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
        timezone_name=timezone_name,
    )


@mcp.tool(
    title="Oura daily data",
    description=(
        "Read rich daily Oura activity, readiness, sleep, heart-rate, stress, recovery, "
        "SpO2, cardiovascular, workout, session, tag and rest-mode data."
    ),
    annotations=READ_ONLY,
    meta=OAUTH_META,
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
    )


@mcp.tool(
    title="Combined health summary",
    description=(
        "Combine Food Reader nutrition with Oura and Withings for a date range, including "
        "daily energy balance, recovery, targets, latest weight and non-causal correlations."
    ),
    annotations=READ_ONLY,
    meta=OAUTH_META,
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
        timezone_name=timezone_name,
        locale=locale,
    )


mcp_http_app = mcp.streamable_http_app()
