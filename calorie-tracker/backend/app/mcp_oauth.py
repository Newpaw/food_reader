import base64
import hashlib
import html
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from mcp.server.auth.middleware.client_auth import (
    AuthenticationError,
    ClientAuthenticator,
)
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from . import crud, database, models
from .settings import settings

logger = logging.getLogger(__name__)

MCP_SCOPES = ["profile:read", "meals:read", "health:read"]
SCOPE_LABELS = {
    "profile:read": "Profil a nutriční cíle",
    "meals:read": "Jídla a nutriční historii",
    "health:read": "Oura, Withings a zdravotní souhrny",
}
AUTHORIZATION_CODE_TTL_SECONDS = 10 * 60
CONSENT_REQUEST_TTL_SECONDS = 10 * 60


class FoodReaderAuthorizationCode(AuthorizationCode):
    record_id: int


class FoodReaderRefreshToken(RefreshToken):
    record_id: int
    resource: str


class FoodReaderAccessToken(AccessToken):
    record_id: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _epoch(value: datetime) -> int:
    return int(value.timestamp())


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def _json_list(value: str) -> list[str]:
    decoded = json.loads(value)
    return [str(item) for item in decoded]


def _valid_redirect_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    if parsed.fragment or parsed.username or parsed.password or not parsed.hostname:
        return False
    if parsed.scheme == "https":
        return True
    return parsed.scheme == "http" and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def _build_consent_request(
    client: OAuthClientInformationFull,
    params: AuthorizationParams,
    scopes: list[str],
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "type": "mcp_oauth_consent",
            "iss": settings.mcp_public_base_url,
            "aud": settings.mcp_resource_url,
            "iat": now,
            "exp": now + CONSENT_REQUEST_TTL_SECONDS,
            "client_id": client.client_id,
            "client_name": client.client_name or "Externí agent",
            "state": params.state,
            "scopes": scopes,
            "code_challenge": params.code_challenge,
            "redirect_uri": str(params.redirect_uri),
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
            "resource": params.resource,
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALG,
    )


def _decode_consent_request(value: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            value,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALG],
            audience=settings.mcp_resource_url,
            issuer=settings.mcp_public_base_url,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=400, detail="Neplatný nebo expirovaný autorizační požadavek."
        ) from exc
    if (
        payload.get("type") != "mcp_oauth_consent"
        or payload.get("resource") != settings.mcp_resource_url
    ):
        raise HTTPException(status_code=400, detail="Neplatný autorizační požadavek.")
    return payload


class FoodReaderOAuthProvider(
    OAuthAuthorizationServerProvider[
        FoodReaderAuthorizationCode, FoodReaderRefreshToken, FoodReaderAccessToken
    ]
):
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with database.SessionLocal() as db:
            row = (
                db.query(models.OAuthClient)
                .filter(models.OAuthClient.client_id == client_id)
                .first()
            )
            if row is None:
                return None
            try:
                payload = json.loads(row.metadata_json)
                if row.client_secret_encrypted:
                    payload["client_secret"] = _decrypt(row.client_secret_encrypted)
                return OAuthClientInformationFull.model_validate(payload)
            except (ValueError, json.JSONDecodeError, InvalidToken):
                logger.exception("Unable to load OAuth client %s", client_id)
                return None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id or not client_info.redirect_uris:
            raise RegistrationError(
                "invalid_client_metadata", "client_id and redirect_uris are required"
            )
        if any(not _valid_redirect_uri(str(uri)) for uri in client_info.redirect_uris):
            raise RegistrationError(
                "invalid_redirect_uri",
                "Redirect URIs must use HTTPS; HTTP is allowed only for localhost development.",
            )
        metadata = client_info.model_dump(mode="json")
        secret = metadata.pop("client_secret", None)
        encoded = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > 64_000:
            raise RegistrationError(
                "invalid_client_metadata", "Client metadata is too large"
            )
        with database.SessionLocal() as db:
            if (
                db.query(models.OAuthClient)
                .filter(models.OAuthClient.client_id == client_info.client_id)
                .first()
            ):
                raise RegistrationError(
                    "invalid_client_metadata", "Client ID is already registered"
                )
            db.add(
                models.OAuthClient(
                    client_id=client_info.client_id,
                    metadata_json=encoded,
                    client_secret_encrypted=_encrypt(secret) if secret else None,
                )
            )
            db.commit()

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        if params.resource != settings.mcp_resource_url:
            raise AuthorizeError(
                "invalid_request",
                "The resource parameter must identify this MCP server",
            )
        scopes = params.scopes or MCP_SCOPES
        if not set(scopes).issubset(MCP_SCOPES):
            raise AuthorizeError(
                "invalid_scope", "One or more requested scopes are not supported"
            )
        request_token = _build_consent_request(client, params, scopes)
        return f"{settings.mcp_public_base_url}/oauth/consent?request={request_token}"

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> FoodReaderAuthorizationCode | None:
        with database.SessionLocal() as db:
            row = (
                db.query(models.OAuthAuthorizationCode)
                .filter(
                    models.OAuthAuthorizationCode.code_hash
                    == _hash_secret(authorization_code),
                    models.OAuthAuthorizationCode.client_id == client.client_id,
                    models.OAuthAuthorizationCode.consumed_at.is_(None),
                )
                .first()
            )
            if row is None:
                return None
            return FoodReaderAuthorizationCode(
                record_id=row.id,
                code=authorization_code,
                scopes=_json_list(row.scopes_json),
                expires_at=row.expires_at.timestamp(),
                client_id=row.client_id,
                code_challenge=row.code_challenge,
                redirect_uri=row.redirect_uri,
                redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
                resource=row.resource,
                subject=str(row.user_id),
            )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: FoodReaderAuthorizationCode,
    ) -> OAuthToken:
        now = _utcnow()
        with database.SessionLocal() as db:
            updated = (
                db.query(models.OAuthAuthorizationCode)
                .filter(
                    models.OAuthAuthorizationCode.id == authorization_code.record_id,
                    models.OAuthAuthorizationCode.client_id == client.client_id,
                    models.OAuthAuthorizationCode.consumed_at.is_(None),
                    models.OAuthAuthorizationCode.expires_at > now,
                )
                .update(
                    {models.OAuthAuthorizationCode.consumed_at: now},
                    synchronize_session=False,
                )
            )
            if updated != 1:
                db.rollback()
                raise TokenError(
                    "invalid_grant", "Authorization code is invalid or already used"
                )
            token = self._issue_token_pair(
                db,
                user_id=int(authorization_code.subject or "0"),
                client_id=str(client.client_id),
                scopes=authorization_code.scopes,
                resource=authorization_code.resource or settings.mcp_resource_url,
            )
            db.commit()
            return token

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> FoodReaderRefreshToken | None:
        now = _utcnow()
        with database.SessionLocal() as db:
            row = (
                db.query(models.OAuthTokenGrant)
                .filter(
                    models.OAuthTokenGrant.refresh_token_hash
                    == _hash_secret(refresh_token),
                    models.OAuthTokenGrant.client_id == client.client_id,
                    models.OAuthTokenGrant.revoked_at.is_(None),
                    models.OAuthTokenGrant.refresh_expires_at > now,
                )
                .first()
            )
            if row is None:
                return None
            return FoodReaderRefreshToken(
                record_id=row.id,
                token=refresh_token,
                client_id=row.client_id,
                scopes=_json_list(row.scopes_json),
                expires_at=_epoch(row.refresh_expires_at),
                subject=str(row.user_id),
                resource=row.resource,
            )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: FoodReaderRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        now = _utcnow()
        with database.SessionLocal() as db:
            updated = (
                db.query(models.OAuthTokenGrant)
                .filter(
                    models.OAuthTokenGrant.id == refresh_token.record_id,
                    models.OAuthTokenGrant.client_id == client.client_id,
                    models.OAuthTokenGrant.revoked_at.is_(None),
                    models.OAuthTokenGrant.refresh_expires_at > now,
                )
                .update(
                    {models.OAuthTokenGrant.revoked_at: now}, synchronize_session=False
                )
            )
            if updated != 1:
                db.rollback()
                raise TokenError(
                    "invalid_grant", "Refresh token is invalid or already used"
                )
            token = self._issue_token_pair(
                db,
                user_id=int(refresh_token.subject or "0"),
                client_id=str(client.client_id),
                scopes=scopes,
                resource=refresh_token.resource,
            )
            db.commit()
            return token

    async def load_access_token(self, token: str) -> FoodReaderAccessToken | None:
        now = _utcnow()
        with database.SessionLocal() as db:
            row = (
                db.query(models.OAuthTokenGrant)
                .filter(
                    models.OAuthTokenGrant.access_token_hash == _hash_secret(token),
                    models.OAuthTokenGrant.resource == settings.mcp_resource_url,
                    models.OAuthTokenGrant.revoked_at.is_(None),
                    models.OAuthTokenGrant.access_expires_at > now,
                )
                .first()
            )
            if row is None:
                return None
            return FoodReaderAccessToken(
                record_id=row.id,
                token=token,
                client_id=row.client_id,
                scopes=_json_list(row.scopes_json),
                expires_at=_epoch(row.access_expires_at),
                resource=row.resource,
                subject=str(row.user_id),
                claims={"iss": settings.mcp_public_base_url, "aud": row.resource},
            )

    async def revoke_token(
        self, token: FoodReaderAccessToken | FoodReaderRefreshToken
    ) -> None:
        with database.SessionLocal() as db:
            db.query(models.OAuthTokenGrant).filter(
                models.OAuthTokenGrant.id == token.record_id
            ).update(
                {models.OAuthTokenGrant.revoked_at: _utcnow()},
                synchronize_session=False,
            )
            db.commit()

    def _issue_token_pair(
        self,
        db,
        *,
        user_id: int,
        client_id: str,
        scopes: list[str],
        resource: str,
    ) -> OAuthToken:
        if resource != settings.mcp_resource_url or not set(scopes).issubset(
            MCP_SCOPES
        ):
            raise TokenError("invalid_grant", "Invalid token audience or scopes")
        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(48)
        now = _utcnow()
        access_expires_at = now + timedelta(
            minutes=settings.MCP_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_expires_at = now + timedelta(
            days=settings.MCP_REFRESH_TOKEN_EXPIRE_DAYS
        )
        db.add(
            models.OAuthTokenGrant(
                access_token_hash=_hash_secret(access_token),
                refresh_token_hash=_hash_secret(refresh_token),
                user_id=user_id,
                client_id=client_id,
                scopes_json=json.dumps(scopes, separators=(",", ":")),
                resource=resource,
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
            )
        )
        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.MCP_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            scope=" ".join(scopes),
            refresh_token=refresh_token,
        )


oauth_provider = FoodReaderOAuthProvider()


def _consent_page(
    request_token: str, payload: dict[str, Any], error: str | None = None
) -> HTMLResponse:
    client_name = html.escape(str(payload.get("client_name") or "Externí agent"))
    scope_items = "".join(
        f"<li>{html.escape(SCOPE_LABELS.get(scope, scope))}</li>"
        for scope in payload.get("scopes", [])
    )
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    escaped_request = html.escape(request_token, quote=True)
    body = f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Připojit Food Reader</title><style>
body{{font-family:system-ui,sans-serif;background:#f5f7f6;color:#17201b;margin:0;padding:32px 16px}}
main{{max-width:520px;margin:auto;background:white;padding:28px;border-radius:18px;box-shadow:0 12px 40px #0001}}
h1{{font-size:1.55rem;margin-top:0}}label{{display:block;font-weight:600;margin-top:16px}}
input{{box-sizing:border-box;width:100%;padding:12px;margin-top:6px;border:1px solid #aeb8b1;border-radius:9px;font:inherit}}
.actions{{display:flex;gap:10px;margin-top:24px}}button{{padding:12px 18px;border:0;border-radius:9px;font:inherit;font-weight:700;cursor:pointer}}
.approve{{background:#176b45;color:white}}.deny{{background:#e7ebe8;color:#26352c}}.error{{color:#a11b1b;font-weight:600}}
small{{color:#56645b}}li{{margin:7px 0}}
</style></head><body><main><h1>Připojit {client_name} k Food Readeru</h1>
<p>Po přihlášení bude agent moci pouze číst:</p><ul>{scope_items}</ul>
<p><small>Agent nemůže měnit ani mazat data. Přístup lze odvolat zrušením OAuth tokenu.</small></p>{error_html}
<form method="post" action="/oauth/consent" autocomplete="on">
<input type="hidden" name="request_token" value="{escaped_request}">
<label for="email">E-mail</label><input id="email" name="email" type="email" autocomplete="username" required>
<label for="password">Heslo</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<div class="actions"><button class="approve" name="action" value="approve" type="submit">Povolit přístup</button>
<button class="deny" name="action" value="deny" type="submit" formnovalidate>Zamítnout</button></div></form>
</main></body></html>"""
    return HTMLResponse(
        body,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


async def show_consent(request: str) -> HTMLResponse:
    payload = _decode_consent_request(request)
    client = await oauth_provider.get_client(str(payload.get("client_id") or ""))
    if client is None or str(payload.get("redirect_uri")) not in {
        str(uri) for uri in client.redirect_uris or []
    }:
        raise HTTPException(status_code=400, detail="OAuth klient již není platný.")
    return _consent_page(request, payload)


async def submit_consent(
    request_token: str = Form(...),
    email: str = Form(""),
    password: str = Form(""),
    action: str = Form(...),
) -> RedirectResponse | HTMLResponse:
    payload = _decode_consent_request(request_token)
    client = await oauth_provider.get_client(str(payload.get("client_id") or ""))
    redirect_uri = str(payload.get("redirect_uri") or "")
    if client is None or redirect_uri not in {
        str(uri) for uri in client.redirect_uris or []
    }:
        raise HTTPException(status_code=400, detail="OAuth klient již není platný.")

    if action != "approve":
        return RedirectResponse(
            construct_redirect_uri(
                redirect_uri, error="access_denied", state=payload.get("state")
            ),
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Cache-Control": "no-store"},
        )

    with database.SessionLocal() as db:
        user = crud.authenticate_user(db, email, password)
        if user is None:
            # Use one generic message for unknown accounts and wrong passwords.
            return _consent_page(request_token, payload, "Přihlášení se nezdařilo.")
        raw_code = secrets.token_urlsafe(32)
        db.add(
            models.OAuthAuthorizationCode(
                code_hash=_hash_secret(raw_code),
                user_id=user.id,
                client_id=client.client_id,
                scopes_json=json.dumps(
                    payload.get("scopes") or MCP_SCOPES, separators=(",", ":")
                ),
                code_challenge=str(payload["code_challenge"]),
                redirect_uri=redirect_uri,
                redirect_uri_provided_explicitly=bool(
                    payload.get("redirect_uri_provided_explicitly")
                ),
                resource=str(payload["resource"]),
                expires_at=_utcnow()
                + timedelta(seconds=AUTHORIZATION_CODE_TTL_SECONDS),
            )
        )
        db.commit()

    return RedirectResponse(
        construct_redirect_uri(redirect_uri, code=raw_code, state=payload.get("state")),
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Cache-Control": "no-store"},
    )


async def revoke_oauth_token(request: Request) -> Response:
    """RFC 7009 revocation with correct support for public (`none`) clients."""

    try:
        client = await ClientAuthenticator(oauth_provider).authenticate_request(request)
    except AuthenticationError as exc:
        return JSONResponse(
            {"error": "unauthorized_client", "error_description": exc.message},
            status_code=401,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )
    form = await request.form()
    raw_token = form.get("token")
    if not isinstance(raw_token, str) or not raw_token:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "token is required"},
            status_code=400,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )
    hint = form.get("token_type_hint")
    loaders = (
        (
            lambda: oauth_provider.load_refresh_token(client, raw_token),
            lambda: oauth_provider.load_access_token(raw_token),
        )
        if hint == "refresh_token"
        else (
            lambda: oauth_provider.load_access_token(raw_token),
            lambda: oauth_provider.load_refresh_token(client, raw_token),
        )
    )
    loaded = None
    for loader in loaders:
        loaded = await loader()
        if loaded is not None:
            break
    if loaded is not None and loaded.client_id == client.client_id:
        await oauth_provider.revoke_token(loaded)
    return Response(
        status_code=200, headers={"Cache-Control": "no-store", "Pragma": "no-cache"}
    )
