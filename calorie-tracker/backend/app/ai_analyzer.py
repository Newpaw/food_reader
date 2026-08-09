import base64
import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from openai import OpenAI

from .settings import settings

IMAGE_ANALYSIS_PROMPT = """
Analyze this food image and return only minified JSON with exactly these keys:
food_description, estimated_calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, notes.
Rules:
- meal_type must be one of breakfast, lunch, dinner, snack
- estimated_calories and all macro values must be integers
- keep food_description short and practical
- keep notes very short
- no markdown, no explanation, no extra keys
""".strip()

TEXT_ANALYSIS_PROMPT = """
Analyze this food description and return only minified JSON with exactly these keys:
food_description, estimated_calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, notes.
Rules:
- meal_type must be one of breakfast, lunch, dinner, snack
- estimated_calories and all macro values must be integers
- keep food_description short and practical
- keep notes very short
- no markdown, no explanation, no extra keys
""".strip()


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI | None:
    if not settings.OPENAI_API_KEY:
        return None
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _completion_controls(model: str, *, max_tokens: int, reasoning_effort: str) -> dict[str, Any]:
    controls: dict[str, Any] = {"max_completion_tokens": max_tokens}
    if model.startswith("gpt-5.6"):
        controls["reasoning_effort"] = reasoning_effort
    return controls


def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _parse_ai_response(response_text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    json_match = re.search(r"({.*})", response_text.replace("\n", ""), re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            result = fallback.copy()
    else:
        result = fallback.copy()

    result.setdefault("food_description", fallback.get("food_description", "Unknown food"))
    result.setdefault("estimated_calories", 1)
    result.setdefault("protein", 0)
    result.setdefault("fat", 0)
    result.setdefault("carbs", 0)
    result.setdefault("fiber", 0)
    result.setdefault("sugar", 0)
    result.setdefault("sodium", 0)
    result.setdefault("meal_type", "snack")
    result.setdefault("notes", "")
    return result


def _build_image_analysis_prompt(
    analysis_context: str | None = None,
    refinement_context: str | None = None,
) -> str:
    prompt = IMAGE_ANALYSIS_PROMPT

    if analysis_context:
        prompt += (
            "\n\nUser-provided meal context that may not be fully visible in the image:\n"
            f"- {analysis_context.strip()}"
            "\nTreat this as trusted context about ingredients, sauces, drinks, missing sides, or portion size."
        )

    if refinement_context:
        prompt += (
            "\n\nUser refinement after the first estimate:\n"
            f"- {refinement_context.strip()}"
            "\nUse this to correct the previous estimate while keeping the same photo as the visual source."
        )

    prompt += (
        "\n\nImportant: separate what you can see from the photo from what the user clarified."
        " Use the image as the primary visual source and the user context as explicit supplemental information."
    )
    return prompt


def analyze_food_image(
    image_path: str,
    analysis_context: str | None = None,
    refinement_context: str | None = None,
) -> dict[str, Any]:
    client = get_openai_client()
    if client is None:
        return {
            "food_description": "Unknown food",
            "estimated_calories": 1,
            "protein": 0,
            "fat": 0,
            "carbs": 0,
            "fiber": 0,
            "sugar": 0,
            "sodium": 0,
            "meal_type": "snack",
            "notes": "OpenAI API key is not configured.",
        }

    base64_image = encode_image_to_base64(image_path)
    prompt = _build_image_analysis_prompt(analysis_context, refinement_context)

    fallback = {
        "food_description": "Unknown food",
        "estimated_calories": 1,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
        "fiber": 0,
        "sugar": 0,
        "sodium": 0,
        "meal_type": "snack",
        "notes": "Could not analyze the image properly.",
    }

    try:
        model = settings.meal_analysis_model
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ],
                }
            ],
            **_completion_controls(model, max_tokens=420, reasoning_effort="none"),
        )
        response_text = response.choices[0].message.content or ""
        return _parse_ai_response(response_text, fallback)
    except Exception as exc:
        fallback["notes"] = f"Error: {exc}"
        return fallback


def analyze_food_text(food_description: str) -> dict[str, Any]:
    client = get_openai_client()
    if client is None:
        return {
            "food_description": food_description,
            "estimated_calories": 1,
            "protein": 0,
            "fat": 0,
            "carbs": 0,
            "fiber": 0,
            "sugar": 0,
            "sodium": 0,
            "meal_type": "snack",
            "notes": "OpenAI API key is not configured.",
        }

    prompt = f'{TEXT_ANALYSIS_PROMPT}\n\nFood description: "{food_description}"'

    fallback = {
        "food_description": food_description,
        "estimated_calories": 1,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
        "fiber": 0,
        "sugar": 0,
        "sodium": 0,
        "meal_type": "snack",
        "notes": "Could not analyze the food description properly.",
    }

    try:
        model = settings.meal_analysis_model
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **_completion_controls(model, max_tokens=360, reasoning_effort="none"),
        )
        response_text = response.choices[0].message.content or ""
        return _parse_ai_response(response_text, fallback)
    except Exception as exc:
        fallback["notes"] = f"Error: {exc}"
        return fallback


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _normalize_meal_type(value: Any) -> str:
    meal_type = str(value or "snack").lower()
    return meal_type if meal_type in {"breakfast", "lunch", "dinner", "snack"} else "snack"


def get_meal_data_from_image(
    image_path: str,
    analysis_context: str | None = None,
    refinement_context: str | None = None,
) -> tuple[int, int, int, int, int, int, int, str, datetime, str | None]:
    analysis = analyze_food_image(image_path, analysis_context, refinement_context)
    food_desc = analysis.get("food_description", "")
    additional_notes = analysis.get("notes", "")
    notes = f"{food_desc}. {additional_notes}" if additional_notes else food_desc

    return (
        _safe_int(analysis.get("estimated_calories", 1), 1),
        _safe_int(analysis.get("protein", 0)),
        _safe_int(analysis.get("fat", 0)),
        _safe_int(analysis.get("carbs", 0)),
        _safe_int(analysis.get("fiber", 0)),
        _safe_int(analysis.get("sugar", 0)),
        _safe_int(analysis.get("sodium", 0)),
        _normalize_meal_type(analysis.get("meal_type")),
        datetime.now(timezone.utc),
        notes,
    )


def get_meal_data_from_text(food_description: str) -> tuple[int, int, int, int, int, int, int, str, datetime, str | None]:
    analysis = analyze_food_text(food_description)
    food_desc = analysis.get("food_description", food_description)
    additional_notes = analysis.get("notes", "")
    notes = f"{food_desc}. {additional_notes}" if additional_notes else food_desc

    return (
        _safe_int(analysis.get("estimated_calories", 1), 1),
        _safe_int(analysis.get("protein", 0)),
        _safe_int(analysis.get("fat", 0)),
        _safe_int(analysis.get("carbs", 0)),
        _safe_int(analysis.get("fiber", 0)),
        _safe_int(analysis.get("sugar", 0)),
        _safe_int(analysis.get("sodium", 0)),
        _normalize_meal_type(analysis.get("meal_type")),
        datetime.now(timezone.utc),
        notes,
    )
