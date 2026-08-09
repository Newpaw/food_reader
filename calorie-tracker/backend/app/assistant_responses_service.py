import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import models
from .ai_analyzer import get_openai_client
from .assistant_service import SYSTEM_PROMPT, TOOLS, _inventory, _safe_zoneinfo, execute_tool
from .settings import settings


logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 8


def _response_tools() -> list[dict[str, Any]]:
    """Convert the legacy Chat Completions function schema to Responses API tools."""
    response_tools: list[dict[str, Any]] = []
    for tool in TOOLS:
        function = tool["function"]
        response_tools.append(
            {
                "type": "function",
                "name": function["name"],
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {"type": "object", "properties": {}}),
                "strict": False,
            }
        )
    return response_tools


def _response_item_to_input(item: Any) -> Any:
    """Turn an SDK response item into an input item while preserving reasoning state."""
    if hasattr(item, "model_dump"):
        return item.model_dump(exclude_none=True)
    return item


def _request_options(model: str) -> dict[str, Any]:
    options: dict[str, Any] = {
        "model": model,
        "tools": _response_tools(),
        "tool_choice": "auto",
        "max_output_tokens": 1000,
        # Food Reader handles conversation state itself. Do not persist private health
        # conversations as Responses API application state.
        "store": False,
    }
    if model.startswith("gpt-5"):
        options["reasoning"] = {"effort": "low"}
    return options


def _runtime_instructions(user: models.User, *, timezone_name: str, locale: str, inventory: dict[str, Any]) -> str:
    local_now = datetime.now(_safe_zoneinfo(timezone_name)).isoformat(timespec="minutes")
    runtime = (
        f"Current user: {user.name}. Current local time: {local_now}. "
        f"Browser timezone: {timezone_name}. Locale: {locale}. "
        f"Available data inventory: {json.dumps(inventory, ensure_ascii=False, default=str)}"
    )
    return f"{SYSTEM_PROMPT}\n\nRuntime context:\n{runtime}"


def _conversation_input(history: list[dict[str, str]], message: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in history[-10:]:
        role = item.get("role")
        content = str(item.get("content") or "")[:3000]
        if role in {"user", "assistant"} and content:
            items.append({"role": role, "content": content})
    items.append({"role": "user", "content": message[:3000]})
    return items


def _localized_failure(locale: str) -> str:
    if locale == "cs":
        return "AI asistent je teď dočasně nedostupný. Zkus to prosím znovu za chvíli."
    return "The AI assistant is temporarily unavailable. Please try again shortly."


def chat_with_food_reader(
    db: Session,
    user: models.User,
    *,
    message: str,
    history: list[dict[str, str]],
    timezone_name: str,
    locale: str,
) -> dict[str, Any]:
    """Run the Food Reader assistant on the Responses API with stateless tool calling."""
    client = get_openai_client()
    if client is None:
        return {
            "available": False,
            "message": "OpenAI API key is not configured.",
            "sources": [],
            "model": None,
        }

    model = settings.assistant_model
    inventory = _inventory(db, user.id)
    instructions = _runtime_instructions(
        user,
        timezone_name=timezone_name,
        locale=locale,
        inventory=inventory,
    )
    request_options = _request_options(model)
    input_items: list[Any] = _conversation_input(history, message)
    used_sources: list[str] = []

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.responses.create(
                instructions=instructions,
                input=input_items,
                **request_options,
            )

            function_calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
            if not function_calls:
                return {
                    "available": True,
                    "message": response.output_text or "",
                    "sources": used_sources,
                    "model": model,
                }

            # With store=False, manually carry forward all output items, including
            # reasoning items, before returning function results to the model.
            input_items.extend(_response_item_to_input(item) for item in response.output)

            for call in function_calls:
                tool_name = call.name
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                result = execute_tool(
                    db,
                    user,
                    tool_name,
                    args,
                    timezone_name=timezone_name,
                    locale=locale,
                )
                if tool_name not in used_sources:
                    used_sources.append(tool_name)

                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
    except Exception:
        logger.exception("Responses API assistant request failed")
        return {
            "available": False,
            "message": _localized_failure(locale),
            "sources": used_sources,
            "model": model,
        }

    return {
        "available": False,
        "message": (
            "AI asistent potřeboval příliš mnoho datových kroků. Zkus dotaz zpřesnit."
            if locale == "cs"
            else "The AI assistant needed too many data-query steps. Please narrow the question."
        ),
        "sources": used_sources,
        "model": model,
    }
