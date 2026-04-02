import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "calorie-tracker"

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///ignored.db")

    from backend.app.database import Base
    from backend.app.deps import get_db
    from backend.app.main import app
    from backend.app.settings import settings

    settings.UPLOAD_DIR = str(tmp_path / "uploads")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def register_and_login(client):
    def _register_and_login(email="tester@example.com", name="Tester", password="strong-pass-123"):
        register_response = client.post(
            "/auth/register",
            json={"email": email, "name": name, "password": password},
        )
        assert register_response.status_code == 200, register_response.text

        login_response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _register_and_login


@pytest.fixture
def ai_stubs(monkeypatch):
    from backend.app.routers import meals_router

    monkeypatch.setattr(
        meals_router,
        "get_meal_data_from_text",
        lambda description: (
            480,
            32,
            18,
            41,
            6,
            5,
            520,
            "lunch",
            __import__("datetime").datetime(2026, 4, 2, 12, 0, tzinfo=__import__("datetime").timezone.utc),
            f"Estimated from: {description}",
        ),
    )
    monkeypatch.setattr(
        meals_router,
        "get_meal_data_from_image",
        lambda image_path, corrections=None: (
            640 if corrections else 590,
            44,
            26,
            38,
            4,
            7,
            610,
            "dinner",
            __import__("datetime").datetime(2026, 4, 2, 18, 30, tzinfo=__import__("datetime").timezone.utc),
            "Updated analysis" if corrections else f"Estimated from image: {Path(image_path).name}",
        ),
    )
