from types import SimpleNamespace


def test_response_tools_are_flattened_for_responses_api():
    from backend.app.assistant_responses_service import _response_tools

    tools = _response_tools()

    assert tools
    assert all(tool["type"] == "function" for tool in tools)
    assert all("name" in tool for tool in tools)
    assert all("function" not in tool for tool in tools)


def test_plain_output_text_removes_markdown_markers():
    from backend.app.assistant_responses_service import _plain_output_text

    assert _plain_output_text("Dej si **40 g bílkovin** a `vodu`.") == "Dej si 40 g bílkovin a vodu."
    assert _plain_output_text("## Doporučení\nJdi 10 minut.") == "Doporučení\nJdi 10 minut."


def test_runtime_instructions_treat_missing_log_as_unknown():
    from backend.app import models
    from backend.app.assistant_responses_service import _runtime_instructions

    user = models.User(name="Test", email="test@example.com", hashed_password="x")
    instructions = _runtime_instructions(
        user,
        timezone_name="Europe/Prague",
        locale="cs",
        inventory={"meals": {"count": 0, "last": None}},
    )

    assert "Missing logged food is UNKNOWN intake" in instructions
    assert "Do not recommend extra calories, protein, or exercise" in instructions
    assert "Return plain text only" in instructions


def test_assistant_uses_responses_api_and_round_trips_tool_output(
    client,
    register_and_login,
    monkeypatch,
):
    from backend.app import assistant_responses_service
    from backend.app.settings import settings

    headers = register_and_login(email="responses@example.com", name="Responses")
    monkeypatch.setattr(settings, "LLM_MODEL", "gpt-5.6-terra")
    monkeypatch.setattr(settings, "ASSISTANT_MODEL", None)

    calls = []

    first_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="function_call",
                name="get_data_inventory",
                arguments="{}",
                call_id="call_inventory",
            )
        ],
        output_text="",
    )
    second_response = SimpleNamespace(
        output=[],
        output_text="Dnes udělej **jednu** konkrétní věc.",
    )

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return first_response if len(calls) == 1 else second_response

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(assistant_responses_service, "get_openai_client", lambda: fake_client)

    response = client.post(
        "/assistant/chat",
        headers=headers,
        json={
            "message": "Co mám udělat teď?",
            "history": [],
            "timezone": "Europe/Prague",
            "locale": "cs",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["available"] is True
    assert payload["message"] == "Dnes udělej jednu konkrétní věc."
    assert payload["sources"] == ["get_data_inventory"]
    assert payload["model"] == "gpt-5.6-terra"

    assert len(calls) == 2
    assert calls[0]["model"] == "gpt-5.6-terra"
    assert calls[0]["reasoning"] == {"effort": "low", "context": "current_turn"}
    assert calls[0]["text"] == {"verbosity": "low"}
    assert calls[0]["max_output_tokens"] == 500
    assert calls[0]["store"] is False
    assert calls[0]["tools"][0]["type"] == "function"
    assert "function" not in calls[0]["tools"][0]

    second_input = calls[1]["input"]
    tool_outputs = [item for item in second_input if isinstance(item, dict) and item.get("type") == "function_call_output"]
    assert len(tool_outputs) == 1
    assert tool_outputs[0]["call_id"] == "call_inventory"
    assert "profile_available" in tool_outputs[0]["output"]


def test_assistant_api_failure_returns_safe_response(client, register_and_login, monkeypatch):
    from backend.app import assistant_responses_service

    headers = register_and_login(email="responses-failure@example.com", name="Responses Failure")

    class FakeResponses:
        def create(self, **kwargs):
            raise RuntimeError("simulated provider failure")

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(assistant_responses_service, "get_openai_client", lambda: fake_client)

    response = client.post(
        "/assistant/chat",
        headers=headers,
        json={
            "message": "Co mám udělat teď?",
            "history": [],
            "timezone": "Europe/Prague",
            "locale": "cs",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["available"] is False
    assert "dočasně nedostupný" in payload["message"]
