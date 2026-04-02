import base64
import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from openai import OpenAI

from .settings import settings


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI | None:
    if not settings.OPENAI_API_KEY:
        return None
    return OpenAI(api_key=settings.OPENAI_API_KEY)


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


def analyze_food_image(image_path: str, corrections: dict[str, str] | None = None) -> dict[str, Any]:
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
    prompt = """
    Analyze this food image and return valid JSON with:
    food_description, estimated_calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, notes.
    meal_type must be one of breakfast, lunch, dinner, or snack.
    """

    if corrections:
        prompt += "\nApply these user corrections before answering:\n"
        prompt += "\n".join(f"- {key}: {value}" for key, value in corrections.items())

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
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ],
                }
            ],
            max_tokens=900,
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

    prompt = f"""
    Analyze this food description and return valid JSON with:
    food_description, estimated_calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, notes.

    Food description: "{food_description}"
    meal_type must be one of breakfast, lunch, dinner, or snack.
    """

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
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
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
    corrections: dict[str, str] | None = None,
) -> tuple[int, int, int, int, int, int, int, str, datetime, str | None]:
    analysis = analyze_food_image(image_path, corrections)
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
