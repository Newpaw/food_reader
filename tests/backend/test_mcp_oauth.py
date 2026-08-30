import base64
import hashlib
from urllib.parse import parse_qs, urlparse

SCOPES = "profile:read meals:read health:read"
RESOURCE = "http://localhost:8000/mcp"
REDIRECT_URI = "https://chatgpt.com/connector/oauth/callback"


def _pkce() -> tuple[str, str]:
    verifier = "a" * 64
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def _register_client(client, token_endpoint_auth_method="none"):
    payload = {
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "client_name": "ChatGPT test",
        "scope": SCOPES,
    }
    if token_endpoint_auth_method is not None:
        payload["token_endpoint_auth_method"] = token_endpoint_auth_method
    response = client.post(
        "/register",
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _authorize(client, client_id: str, email: str, password: str):
    verifier, challenge = _pkce()
    response = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "state-123",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302, response.text
    consent_url = urlparse(response.headers["location"])
    assert consent_url.path == "/oauth/consent"
    request_token = parse_qs(consent_url.query)["request"][0]

    page = client.get(f"/oauth/consent?request={request_token}")
    assert page.status_code == 200
    assert "ChatGPT test" in page.text

    approval = client.post(
        "/oauth/consent",
        data={
            "request_token": request_token,
            "email": email,
            "password": password,
            "action": "approve",
        },
        follow_redirects=False,
    )
    assert approval.status_code == 303, approval.text
    callback = urlparse(approval.headers["location"])
    callback_params = parse_qs(callback.query)
    assert callback_params["state"] == ["state-123"]
    return verifier, callback_params["code"][0]


def _exchange(
    client, client_id: str, verifier: str, code: str, client_secret: str | None = None
):
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
        "resource": RESOURCE,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    response = client.post(
        "/token",
        data=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _mcp_request(client, access_token: str, method: str, params=None, request_id=1):
    return client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        },
    )


def test_oauth_metadata_and_bearer_challenge(client):
    metadata = client.get("/.well-known/oauth-authorization-server")
    assert metadata.status_code == 200
    assert metadata.json()["code_challenge_methods_supported"] == ["S256"]
    assert "none" in metadata.json()["token_endpoint_auth_methods_supported"]
    assert metadata.json()["registration_endpoint"].endswith("/register")

    protected = client.get("/.well-known/oauth-protected-resource/mcp")
    assert protected.status_code == 200
    assert protected.json()["resource"] == RESOURCE
    assert protected.json()["scopes_supported"] == SCOPES.split()

    root_alias = client.get("/.well-known/oauth-protected-resource")
    assert root_alias.status_code == 200
    assert root_alias.json()["resource"] == RESOURCE

    unauthorized = _mcp_request(client, "not-a-token", "tools/list")
    assert unauthorized.status_code == 401
    assert (
        'resource_metadata="http://localhost:8000/.well-known/oauth-protected-resource/mcp"'
        in unauthorized.headers["www-authenticate"]
    )


def test_full_oauth_pkce_flow_and_mcp_tools(client):
    client.post(
        "/auth/register",
        json={
            "email": "mcp@example.com",
            "name": "MCP User",
            "password": "strong-pass-123",
        },
    )
    registered = _register_client(client)
    verifier, code = _authorize(
        client, registered["client_id"], "mcp@example.com", "strong-pass-123"
    )
    tokens = _exchange(client, registered["client_id"], verifier, code)
    assert tokens["token_type"] == "Bearer"
    assert tokens["scope"] == SCOPES
    assert tokens["refresh_token"]

    reused = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": registered["client_id"],
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
    )
    assert reused.status_code == 400
    assert reused.json()["error"] == "invalid_grant"

    initialized = _mcp_request(
        client,
        tokens["access_token"],
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"},
        },
    )
    assert initialized.status_code == 200, initialized.text
    assert initialized.json()["result"]["serverInfo"]["name"] == "Food Reader"

    tools = _mcp_request(client, tokens["access_token"], "tools/list", request_id=2)
    assert tools.status_code == 200, tools.text
    names = {tool["name"] for tool in tools.json()["result"]["tools"]}
    assert names == {
        "get_data_inventory",
        "get_profile",
        "get_meals",
        "get_withings_measurements",
        "get_oura_daily",
        "get_health_summary",
    }
    assert all(
        tool["annotations"]["readOnlyHint"] is True
        for tool in tools.json()["result"]["tools"]
    )

    profile = _mcp_request(
        client,
        tokens["access_token"],
        "tools/call",
        {"name": "get_profile", "arguments": {"timezone_name": "Europe/Prague"}},
        request_id=3,
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["result"]["structuredContent"]["name"] == "MCP User"


def test_oauth_rejects_wrong_resource_pkce_and_credentials(client):
    client.post(
        "/auth/register",
        json={
            "email": "secure@example.com",
            "name": "Secure",
            "password": "strong-pass-123",
        },
    )
    registered = _register_client(client)
    _, challenge = _pkce()
    wrong_resource = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": registered["client_id"],
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": "https://attacker.example/mcp",
        },
        follow_redirects=False,
    )
    assert wrong_resource.status_code == 302
    assert parse_qs(urlparse(wrong_resource.headers["location"]).query)["error"] == [
        "invalid_request"
    ]

    verifier, challenge = _pkce()
    start = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": registered["client_id"],
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
        },
        follow_redirects=False,
    )
    request_token = parse_qs(urlparse(start.headers["location"]).query)["request"][0]
    bad_login = client.post(
        "/oauth/consent",
        data={
            "request_token": request_token,
            "email": "secure@example.com",
            "password": "wrong",
            "action": "approve",
        },
    )
    assert bad_login.status_code == 200
    assert "Přihlášení se nezdařilo" in bad_login.text

    approval = client.post(
        "/oauth/consent",
        data={
            "request_token": request_token,
            "email": "secure@example.com",
            "password": "strong-pass-123",
            "action": "approve",
        },
        follow_redirects=False,
    )
    code = parse_qs(urlparse(approval.headers["location"]).query)["code"][0]
    wrong_pkce = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": registered["client_id"],
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": "b" * 64,
        },
    )
    assert wrong_pkce.status_code == 400
    assert wrong_pkce.json()["error"] == "invalid_grant"

    # A failed verifier must not consume the authorization code.
    recovered = _exchange(client, registered["client_id"], verifier, code)
    assert recovered["access_token"]


def test_confidential_dcr_client_secret_is_encrypted_and_usable(client):
    import json

    from backend.app import database, models

    client.post(
        "/auth/register",
        json={
            "email": "secret@example.com",
            "name": "Secret",
            "password": "strong-pass-123",
        },
    )
    registered = _register_client(client, token_endpoint_auth_method=None)
    assert registered["token_endpoint_auth_method"] == "client_secret_post"
    assert registered["client_secret"]

    with database.SessionLocal() as db:
        stored = (
            db.query(models.OAuthClient)
            .filter_by(client_id=registered["client_id"])
            .one()
        )
        assert registered["client_secret"] not in stored.metadata_json
        assert registered["client_secret"] not in stored.client_secret_encrypted
        assert "client_secret" not in json.loads(stored.metadata_json)

    verifier, code = _authorize(
        client, registered["client_id"], "secret@example.com", "strong-pass-123"
    )
    tokens = _exchange(
        client,
        registered["client_id"],
        verifier,
        code,
        client_secret=registered["client_secret"],
    )
    assert tokens["access_token"]


def test_refresh_tokens_rotate_and_revocation_blocks_access(client):
    client.post(
        "/auth/register",
        json={
            "email": "rotate@example.com",
            "name": "Rotate",
            "password": "strong-pass-123",
        },
    )
    registered = _register_client(client)
    verifier, code = _authorize(
        client, registered["client_id"], "rotate@example.com", "strong-pass-123"
    )
    first = _exchange(client, registered["client_id"], verifier, code)

    refreshed = client.post(
        "/token",
        data={
            "grant_type": "refresh_token",
            "client_id": registered["client_id"],
            "refresh_token": first["refresh_token"],
            "scope": SCOPES,
            "resource": RESOURCE,
        },
    )
    assert refreshed.status_code == 200, refreshed.text
    second = refreshed.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert _mcp_request(client, first["access_token"], "tools/list").status_code == 401

    reused_refresh = client.post(
        "/token",
        data={
            "grant_type": "refresh_token",
            "client_id": registered["client_id"],
            "refresh_token": first["refresh_token"],
        },
    )
    assert reused_refresh.status_code == 400

    revoked = client.post(
        "/revoke",
        data={
            "client_id": registered["client_id"],
            "token": second["access_token"],
            "token_type_hint": "access_token",
        },
    )
    assert revoked.status_code == 200
    assert _mcp_request(client, second["access_token"], "tools/list").status_code == 401
