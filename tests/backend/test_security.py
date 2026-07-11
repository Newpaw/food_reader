from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.security import SecurityMiddleware
from backend.app.settings import Settings


def build_client(*, max_body_bytes=1024, auth_limit=2, analysis_limit=2):
    app = FastAPI()
    app.add_middleware(
        SecurityMiddleware,
        max_body_bytes=max_body_bytes,
        auth_limit=auth_limit,
        auth_window_seconds=60,
        analysis_limit=analysis_limit,
        analysis_window_seconds=60,
    )

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    @app.post("/me/meals/text")
    def analyze_text(payload: dict):
        return payload

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return TestClient(app)


def test_security_headers_are_added():
    client = build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cache-control"] == "no-store"


def test_request_body_limit_is_enforced():
    client = build_client(max_body_bytes=32)

    response = client.post("/me/meals/text", json={"description": "x" * 100})

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body is too large."


def test_auth_rate_limit_returns_retry_after():
    client = build_client(auth_limit=2)

    assert client.post("/auth/login").status_code == 200
    assert client.post("/auth/login").status_code == 200
    response = client.post("/auth/login")

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1


def test_analysis_rate_limit_is_separate_from_auth_limit():
    client = build_client(auth_limit=1, analysis_limit=2)

    assert client.post("/auth/login").status_code == 200
    assert client.post("/me/meals/text", json={"description": "meal one"}).status_code == 200
    assert client.post("/me/meals/text", json={"description": "meal two"}).status_code == 200
    assert client.post("/me/meals/text", json={"description": "meal three"}).status_code == 429


def test_production_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    settings = Settings(_env_file=None)

    try:
        settings.validate_runtime_security()
    except RuntimeError as exc:
        assert "JWT_SECRET" in str(exc)
    else:
        raise AssertionError("Production should reject the default JWT secret")
