import jwt


def test_register_login_and_get_current_user(client, register_and_login):
    headers = register_and_login()

    response = client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "tester@example.com"


def test_login_token_lasts_for_one_week(client):
    register_response = client.post(
        "/auth/register",
        json={"email": "week@example.com", "name": "Week Tester", "password": "strong-pass-123"},
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        "/auth/login",
        json={"email": "week@example.com", "password": "strong-pass-123"},
    )
    assert login_response.status_code == 200, login_response.text

    token_payload = jwt.decode(
        login_response.json()["access_token"],
        "test-secret",
        algorithms=["HS256"],
    )
    assert token_payload["exp"] - token_payload["iat"] == 7 * 24 * 60 * 60


def test_text_meal_crud_and_summary_with_timezone_offset(client, register_and_login, ai_stubs):
    headers = register_and_login()

    create_response = client.post(
        "/me/meals/text",
        headers=headers,
        json={
            "food_description": "Late pasta dinner",
            "calories": 520,
            "protein": 22,
            "fat": 18,
            "carbs": 62,
            "fiber": 5,
            "sugar": 8,
            "sodium": 540,
            "meal_type": "dinner",
            "consumed_at": "2026-04-01T23:30:00Z",
            "notes": "Home cooked",
        },
    )

    assert create_response.status_code == 200, create_response.text
    meal = create_response.json()
    meal_id = meal["id"]
    assert meal["image_url"] == "/assets/images/text-meal-placeholder.svg"
    assert meal["consumed_at"] == "2026-04-01T23:30:00Z"

    list_response = client.get(
        "/me/meals",
        headers=headers,
        params={"frm": "2026-04-01T00:00:00Z", "to": "2026-04-03T00:00:00Z"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["consumed_at"] == "2026-04-01T23:30:00Z"

    summary_response = client.get(
        "/me/summary",
        headers=headers,
        params={
            "frm": "2026-04-01T00:00:00Z",
            "to": "2026-04-03T00:00:00Z",
            "tz_offset_minutes": -120,
        },
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["days"] == [{"date": "2026-04-02", "total_calories": 520, "meals": 1}]

    update_response = client.put(
        f"/me/meals/{meal_id}",
        headers=headers,
        json={"calories": 560, "notes": "Adjusted after weighing"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["calories"] == 560

    reanalyze_response = client.post(
        f"/me/meals/{meal_id}/reanalyze",
        headers=headers,
        json={"corrections": {"food_type": "This was text-only"}},
    )
    assert reanalyze_response.status_code == 400

    delete_response = client.delete(f"/me/meals/{meal_id}", headers=headers)
    assert delete_response.status_code == 204

    final_list = client.get("/me/meals", headers=headers)
    assert final_list.status_code == 200
    assert final_list.json() == []


def test_text_meal_rejects_naive_datetime(client, register_and_login):
    headers = register_and_login()

    response = client.post(
        "/me/meals/text",
        headers=headers,
        json={
            "food_description": "Naive datetime meal",
            "calories": 450,
            "protein": 18,
            "fat": 12,
            "carbs": 52,
            "fiber": 4,
            "sugar": 7,
            "sodium": 410,
            "meal_type": "lunch",
            "consumed_at": "2026-04-01T23:30:00",
        },
    )

    assert response.status_code == 422


def test_summary_groups_using_timezone_name_for_dst_boundaries(client, register_and_login):
    headers = register_and_login()

    create_response = client.post(
        "/me/meals/text",
        headers=headers,
        json={
            "food_description": "Late DST meal",
            "calories": 430,
            "protein": 22,
            "fat": 16,
            "carbs": 48,
            "fiber": 5,
            "sugar": 6,
            "sodium": 390,
            "meal_type": "dinner",
            "consumed_at": "2026-10-25T22:30:00Z",
        },
    )

    assert create_response.status_code == 200, create_response.text

    summary_response = client.get(
        "/me/summary",
        headers=headers,
        params={
            "frm": "2026-10-25T00:00:00Z",
            "to": "2026-10-27T00:00:00Z",
            "tz_name": "Europe/Prague",
        },
    )

    assert summary_response.status_code == 200, summary_response.text
    assert summary_response.json()["days"] == [{"date": "2026-10-25", "total_calories": 430, "meals": 1}]


def test_image_meal_upload_and_reanalysis(client, register_and_login, ai_stubs):
    headers = register_and_login()

    create_response = client.post(
        "/me/meals",
        headers=headers,
        files={"image": ("meal.jpg", b"fake-image", "image/jpeg")},
    )
    assert create_response.status_code == 200, create_response.text
    meal = create_response.json()
    assert meal["image_url"].startswith("/uploads/1/")
    assert meal["calories"] == 590

    reanalyze_response = client.post(
        f"/me/meals/{meal['id']}/reanalyze",
        headers=headers,
        json={"corrections": {"protein": "This included extra chicken"}},
    )
    assert reanalyze_response.status_code == 200
    assert reanalyze_response.json()["calories"] == 640
    assert "Reanalysis with corrections" in reanalyze_response.json()["notes"]


def test_user_cannot_delete_someone_elses_meal(client, register_and_login, ai_stubs):
    owner_headers = register_and_login()
    other_headers = register_and_login(email="other@example.com", name="Other")

    create_response = client.post(
        "/me/meals/text",
        headers=owner_headers,
        json={
            "food_description": "Rice bowl",
            "calories": 450,
            "protein": 20,
            "fat": 12,
            "carbs": 58,
            "fiber": 4,
            "sugar": 6,
            "sodium": 410,
            "meal_type": "lunch",
            "consumed_at": "2026-04-02T12:00:00Z",
        },
    )
    meal_id = create_response.json()["id"]

    delete_response = client.delete(f"/me/meals/{meal_id}", headers=other_headers)
    assert delete_response.status_code == 404
