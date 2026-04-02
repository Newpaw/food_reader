def test_profile_create_update_and_targets(client, register_and_login):
    headers = register_and_login()

    create_response = client.post(
        "/profile",
        headers=headers,
        json={
            "height_cm": 180,
            "weight_kg": 82,
            "age": 31,
            "gender": "male",
            "activity_level": "moderately_active",
            "goal": "maintenance",
            "dietary_preference": "high_protein",
        },
    )
    assert create_response.status_code == 201, create_response.text
    profile = create_response.json()
    assert profile["target_calories"] is not None
    assert profile["target_protein_g"] is not None

    targets_response = client.get("/profile/targets", headers=headers)
    assert targets_response.status_code == 200
    targets = targets_response.json()
    assert targets["calories"] > 0
    assert "Calculated using Mifflin-St Jeor equation" in targets["calculation_method"]

    custom_response = client.put(
        "/profile",
        headers=headers,
        json={
            "custom_calories": 2400,
            "custom_protein_g": 190,
            "custom_carbs_g": 180,
            "custom_fats_g": 90,
            "custom_fiber_g": 35,
        },
    )
    assert custom_response.status_code == 200, custom_response.text
    assert custom_response.json()["target_calories"] == 2400

    custom_targets_response = client.get("/profile/targets", headers=headers)
    assert custom_targets_response.status_code == 200
    assert custom_targets_response.json()["calculation_method"] == "Custom values provided by user"


def test_profile_targets_disappear_when_required_biometrics_are_removed(client, register_and_login):
    headers = register_and_login()

    create_response = client.post(
        "/profile",
        headers=headers,
        json={
            "height_cm": 165,
            "weight_kg": 64,
            "age": 28,
            "gender": "female",
        },
    )
    assert create_response.status_code == 201

    clear_response = client.put(
        "/profile",
        headers=headers,
        json={"weight_kg": None},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["target_calories"] is None

    targets_response = client.get("/profile/targets", headers=headers)
    assert targets_response.status_code == 404
