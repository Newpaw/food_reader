import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .logger import RequestLoggingMiddleware, get_logger
from .mcp_oauth import MCP_SCOPES, revoke_oauth_token, show_consent, submit_consent
from .mcp_server import mcp, mcp_http_app
from .routers import (
    assistant_router,
    auth_router,
    meals_router,
    oura_router,
    profile_router,
    users_router,
    withings_router,
)
from .settings import settings

logger = get_logger(__name__)

# Starlette validates the static directory when StaticFiles is constructed,
# before FastAPI's lifespan hook runs. Ensure it exists for clean installs and CI.
os.makedirs(settings.upload_dir_path, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if (
        settings.mcp_public_base_url.startswith("https://")
        and settings.JWT_SECRET == "change-me-in-production"
    ):
        raise RuntimeError("JWT_SECRET must be changed before exposing the MCP OAuth server")
    init_db()
    logger.info("Application started")
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Calorie Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir_path)), name="uploads")

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(meals_router.router)
app.include_router(profile_router.router)
app.include_router(withings_router.router)
app.include_router(oura_router.router)
app.include_router(assistant_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.add_api_route("/oauth/consent", show_consent, methods=["GET"], response_class=HTMLResponse)
app.add_api_route("/oauth/consent", submit_consent, methods=["POST"], response_model=None)
app.add_api_route("/revoke", revoke_oauth_token, methods=["POST"], response_model=None)


@app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
def oauth_authorization_server_metadata() -> dict[str, object]:
    base = settings.mcp_public_base_url
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "revocation_endpoint": f"{base}/revoke",
        "scopes_supported": MCP_SCOPES,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": [
            "none",
            "client_secret_post",
            "client_secret_basic",
        ],
        "code_challenge_methods_supported": ["S256"],
    }


@app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
def oauth_protected_resource_metadata() -> dict[str, object]:
    """Compatibility alias for clients that probe the origin-level RFC 9728 URL."""

    return {
        "resource": settings.mcp_resource_url,
        "authorization_servers": [settings.mcp_public_base_url],
        "scopes_supported": MCP_SCOPES,
        "bearer_methods_supported": ["header"],
        "resource_name": "Food Reader MCP",
    }


# Keep this catch-all mount last so existing FastAPI routes retain precedence.
app.mount("/", mcp_http_app, name="mcp")
