import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import models
from .ai_analyzer import get_openai_client
from .assistant_meal_tools import MEAL_MUTATION_TOOL_NAMES, MEAL_MUTATION_TOOLS, execute_meal_mutation_tool
from .assistant_service import SYSTEM_PROMPT, TOOLS, _inventory, _safe_zoneinfo, execute_tool
from .oura_models import OuraDailyMetric
from .oura_service import parse_oura_details
from .settings import settings


logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 8

ACTION_FIRST_GUARD = """
Additional product rules for this turn:
- Missing logged food is UNKNOWN intake, not zero intake. Never assume the user has eaten nothing just because no meal is recorded.
- If today's meal log is empty or clearly incomplete, the first recommendation must be to log what the user has already eaten today. Do not recommend extra calories, protein, or exercise from an incomplete food log.
- Give exactly one primary action. A short reason may follow, but do not add competing alternatives.
- Use concrete quantities only when the available data supports them.
- Return plain text only. Do not use Markdown formatting markers such as **, __, #, or backticks.
- Keep the final answer compact enough to scan on a phone: normally one action sentence plus at most two short evidence lines.
""".strip()

MEAL_WRITE_RULES = """
Meal logging exception to the base read-only rule:
- You may create, update, and delete meal records only through add_meal, update_meal, and delete_meal. All other Food Reader data remains read-only.
- Call add_meal when the user clearly reports food or drink they actually consumed in first person, or explicitly asks to log it. Do not log hypothetical, planned, recommended, or merely discussed food.
- If it is genuinely ambiguous whether food was consumed or only being discussed, ask one short clarification instead of writing.
- For update_meal and delete_meal, act only on a clear correction/removal request. Use get_meals first whenever needed to identify the exact meal_id. Never guess an id.
- A clear explicit delete/remove request does not need a second confirmation once the meal is uniquely identified.
- Never create duplicate meal records for the same user statement within one turn.
- After a successful write, briefly confirm what was created, changed, or deleted. If a tool returns an error, say that the change was not saved.
""".strip()


def _enriched_read_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for tool in TOOLS:
        function = tool.get("function") or {}
        if function.get("name") == "get_oura_daily":
            function = {
                **function,
                "description": (
                    "Read rich Oura daily health context including activity and sedentary time, calorie expenditure, steps, "
                    "readiness contributors and temperature deviation, sleep stages/efficiency/HRV/heart rate/breathing, "
                    "stress/recovery, workouts, SpO2, resilience, cardiovascular age, VO2 max, heart-rate summaries, "
                    "sessions and tags when available."
                ),
            }
            tools.append({**tool, "function": function})
        else:
            tools.append(tool)
    return tools


ALL_TOOLS = [*_enriched_read_tools(), *MEAL_MUTATION_TOOLS]
ACTIVE_SYSTEM_PROMPT = SYSTEM_PROMPT.replace(
    "private read-only assistant",
    "private nutrition and health assistant",
).replace(
    "- The assistant is read-only. Do not claim to edit, delete, sync, or create Food Reader records.",
    "- Meal records may be created, updated, or deleted only through the dedicated meal mutation tools. Other Food Reader data remains read-only.",
)


def _response_tools() -> list[dict[str, Any]]:
    """Convert shared read tools and meal write tools to Responses API tools."""
    response_tools: list[dict[str, Any]] = []
    for tool in ALL_TOOLS:
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
        "max_output_tokens": 500,
        "text": {"verbosity": "low"},
        "store": False,
    }
    if model.startswith("gpt-5"):
        options["reasoning"] = {"effort": "low", "context": "current_turn"}
    return options


def _runtime_instructions(user: models.User, *, timezone_name: str, locale: str, inventory: dict[str, Any]) -> str:
    local_now = datetime.now(_safe_zoneinfo(timezone_name)).isoformat(timespec="minutes")
    runtime = (
        f"Current user: {user.name}. Current local time: {local_now}. "
        f"Browser timezone: {timezone_name}. Locale: {locale}. "
        f"Available data inventory: {json.dumps(inventory, ensure_ascii=False, default=str)}"
    )
    return f"{ACTIVE_SYSTEM_PROMPT}\n\n{MEAL_WRITE_RULES}\n\n{ACTION_FIRST_GUARD}\n\nRuntime context:\n{runtime}"


def _conversation_input(history: list[dict[str, str]], message: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in history[-10:]:
        role = item.get("role")
        content = str(item.get("content") or "")[:3000]
        if role in {"user", "assistant"} and content:
            items.append({"role": role, "content": content})
    items.append({"role": "user", "content": message[:3000]})
    return items


def _plain_output_text(value: str) -> str:
    """Keep assistant output readable in the plain-text chat bubble."""
    text = str(value or "").strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.*?)__", r"\1", text, flags=re.DOTALL)
    text = text.replace("`", "")
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    return text.strip()


def _localized_failure(locale: str) -> str:
    if locale == "cs":
        return "AI asistent je teď dočasně nedostupný. Zkus to prosím znovu za chvíli."
    return "The AI assistant is temporarily unavailable. Please try again shortly."


def _augment_oura_result(db: Session, user_id: int, result: dict[str, Any]) -> dict[str, Any]:
    rows = result.get("rows")
    if not isinstance(rows, list) or not rows:
        return result
    days = [str(row.get("day")) for row in rows if isinstance(row, dict) and row.get("day")]
    if not days:
        return result
    metrics = (
        db.query(OuraDailyMetric)
        .filter(OuraDailyMetric.user_id == user_id, OuraDailyMetric.day.in_(days))
        .all()
    )
    by_day = {metric.day: metric for metric in metrics}
    for row in rows:
        if not isinstance(row, dict):
            continue
        metric = by_day.get(str(row.get("day")))
        if metric is None:
            continue
        row.update(
            {
                "activity_target_calories": metric.activity_target_calories,
                "average_met_minutes": metric.average_met_minutes,
                "equivalent_walking_distance_m": metric.equivalent_walking_distance_m,
                "sedentary_seconds": metric.sedentary_seconds,
                "resting_seconds": metric.resting_seconds,
                "low_activity_seconds": metric.low_activity_seconds,
                "medium_activity_seconds": metric.medium_activity_seconds,
                "high_activity_seconds": metric.high_activity_seconds,
                "non_wear_seconds": metric.non_wear_seconds,
                "inactivity_alerts": metric.inactivity_alerts,
                "temperature_deviation_c": metric.temperature_deviation_c,
                "temperature_trend_deviation_c": metric.temperature_trend_deviation_c,
                "time_in_bed_seconds": metric.time_in_bed_seconds,
                "awake_seconds": metric.awake_seconds,
                "light_sleep_seconds": metric.light_sleep_seconds,
                "deep_sleep_seconds": metric.deep_sleep_seconds,
                "rem_sleep_seconds": metric.rem_sleep_seconds,
                "sleep_latency_seconds": metric.sleep_latency_seconds,
                "sleep_efficiency": metric.sleep_efficiency,
                "average_heart_rate_bpm": metric.average_heart_rate_bpm,
                "average_breaths_per_minute": metric.average_breaths_per_minute,
                "bedtime_start": metric.bedtime_start,
                "bedtime_end": metric.bedtime_end,
                "spo2_average_percent": metric.spo2_average_percent,
                "resilience_level": metric.resilience_level,
                "vascular_age_years": metric.vascular_age_years,
                "vo2_max": metric.vo2_max,
                "heart_rate_average_bpm": metric.heart_rate_average_bpm,
                "heart_rate_min_bpm": metric.heart_rate_min_bpm,
                "heart_rate_max_bpm": metric.heart_rate_max_bpm,
                "heart_rate_samples": metric.heart_rate_samples,
                "details": parse_oura_details(metric.details_json),
            }
        )
    return result


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
                    "message": _plain_output_text(response.output_text or ""),
                    "sources": used_sources,
                    "model": model,
                }

            input_items.extend(_response_item_to_input(item) for item in response.output)

            for call in function_calls:
                tool_name = call.name
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if tool_name in MEAL_MUTATION_TOOL_NAMES:
                    result = execute_meal_mutation_tool(
                        db,
                        user,
                        tool_name,
                        args,
                        timezone_name=timezone_name,
                    )
                else:
                    result = execute_tool(
                        db,
                        user,
                        tool_name,
                        args,
                        timezone_name=timezone_name,
                        locale=locale,
                    )
                    if tool_name == "get_oura_daily" and isinstance(result, dict):
                        result = _augment_oura_result(db, user.id, result)
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
