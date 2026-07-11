from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from fastapi import UploadFile
from PIL import Image


def _profile_payload():
    return {
        "height_cm": 181,
        "weight_kg": 87,
        "target_weight_kg": 80,
        "desired_weekly_loss_percent": 0.6,
        "age": 40,
        "gender": "male",
        "activity_level": "lightly_active",
        "goal": "weight_loss",
        "dietary_preference": "high_protein",
    }


def _meal_payload(calories=600, protein=45, fiber=8):
    return {
        "food_description": "Chicken, potatoes and vegetables",
        "calories": calories,
        "protein": protein,
        "fat": 18,
        "carbs": 65,
        "fiber": fiber,
        "sugar": 8,
        "sodium": 600,
        "meal_type": "lunch",
        "consumed_at": datetime.now(timezone.utc).isoformat(),
    }


def test_weight_loss_targets_prioritize_protein(client, register_and_login):
    headers = register_and_login()
    response = client.post("/profile", headers=headers, json=_profile_payload())
    assert response.status_code == 201, response.text
    profile = response.json()
    assert profile["goal"] == "weight_loss"
    assert profile["target_weight_kg"] == 80
    assert 140 <= profile["target_protein_g"] <= 190
    assert profile["target_calories"] < profile["tdee"]


def test_today_coach_and_checkin(client, register_and_login):
    headers = register_and_login()
    assert client.post("/profile", headers=headers, json=_profile_payload()).status_code == 201
    assert client.post("/me/meals/text", headers=headers, json=_meal_payload()).status_code == 200

    checkin = client.put(
        "/coach/checkin",
        headers=headers,
        json={"hunger": 4, "energy": 3, "sleep_hours": 7.0, "steps": 6500, "trained": True, "timezone": "Europe/Prague"},
    )
    assert checkin.status_code == 200, checkin.text

    response = client.get("/coach/today", headers=headers, params={"timezone": "Europe/Prague"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["calories"]["current"] == 600
    assert data["protein"]["current"] == 45
    assert data["checkin"]["hunger"] == 4
    assert data["next_action"]["action_type"] in {"manage_hunger", "increase_protein", "increase_fiber", "maintain"}


def test_weekly_average_includes_unlogged_days(client, register_and_login):
    headers = register_and_login()
    assert client.post("/profile", headers=headers, json=_profile_payload()).status_code == 201
    assert client.post("/me/meals/text", headers=headers, json=_meal_payload(calories=1400)).status_code == 200

    response = client.get("/coach/weekly", headers=headers, params={"timezone": "Europe/Prague", "days": 7})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["logged_days"] == 1
    assert data["average_calories_logged_days"] == 1400
    assert data["average_calories_all_days"] == 200
    assert data["logging_completeness_percent"] == 14
    assert data["adaptive_target"]["eligible"] is False


def test_private_media_url_requires_valid_signature(client, register_and_login, ai_stubs):
    headers = register_and_login()
    response = client.post(
        "/me/meals",
        headers=headers,
        files={"image": ("meal.jpg", b"placeholder", "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    image_url = response.json()["image_url"]
    parsed = urlparse(image_url)
    token = parse_qs(parsed.query)["token"][0]

    valid = client.get(image_url)
    assert valid.status_code == 200
    invalid = client.get(f"{parsed.path}?token={token[:-1]}x")
    assert invalid.status_code == 403


def test_image_processing_reencodes_and_rejects_non_images(tmp_path, monkeypatch):
    from backend.app.image_processing import store_private_meal_image
    from backend.app.settings import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    image = Image.new("RGB", (2200, 1200), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    upload = UploadFile(filename="meal.png", file=BytesIO(buffer.getvalue()), headers={"content-type": "image/png"})

    import asyncio

    path = asyncio.run(store_private_meal_image(upload, 7))
    with Image.open(path) as stored:
        assert stored.format == "JPEG"
        assert max(stored.size) <= settings.MAX_IMAGE_DIMENSION

    invalid = UploadFile(filename="bad.jpg", file=BytesIO(b"not an image"), headers={"content-type": "image/jpeg"})
    try:
        asyncio.run(store_private_meal_image(invalid, 7))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Invalid image was accepted")
