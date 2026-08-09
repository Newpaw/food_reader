import logging
import os
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import models
from .ai_analyzer import get_meal_data_from_text


logger = logging.getLogger(__name__)
VALID_MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}
NUTRITION_FIELDS = ("calories", "protein", "fat", "carbs", "fiber", "sugar", "sodium")

MEAL_MUTATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_meal",
            "description": (
                "Create a meal record for food or drink the authenticated user actually consumed. "
                "Use only for real consumed food, never hypothetical/planned food. Nutrition fields are optional; "
                "missing values are estimated from food_description by the existing Food Reader meal analyzer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "food_description": {
                        "type": "string",
                        "description": "What the user ate or drank, including quantity/context when known.",
                    },
                    "calories": {"type": ["integer", "null"], "minimum": 0},
                    "protein": {"type": ["integer", "null"], "minimum": 0},
                    "fat": {"type": ["integer", "null"], "minimum": 0},
                    "carbs": {"type": ["integer", "null"], "minimum": 0},
                    "fiber": {"type": ["integer", "null"], "minimum": 0},
                    "sugar": {"type": ["integer", "null"], "minimum": 0},
                    "sodium": {"type": ["integer", "null"], "minimum": 0},
                    "meal_type": {
                        "type": ["string", "null"],
                        "enum": ["breakfast", "lunch", "dinner", "snack", None],
                    },
                    "consumed_at": {
                        "type": ["string", "null"],
                        "description": "ISO 8601 date-time with timezone when known. Omit to infer from description/current time.",
                    },
                    "notes": {"type": ["string", "null"]},
                },
                "required": ["food_description"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_meal",
            "description": (
                "Update one existing meal belonging to the authenticated user. Resolve the exact meal_id with get_meals first; "
                "never guess an id. If food_description is supplied, nutrition is re-estimated from that corrected description, "
                "while explicitly supplied nutrition values override the estimate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {"type": "integer", "minimum": 1},
                    "food_description": {"type": ["string", "null"]},
                    "calories": {"type": ["integer", "null"], "minimum": 0},
                    "protein": {"type": ["integer", "null"], "minimum": 0},
                    "fat": {"type": ["integer", "null"], "minimum": 0},
                    "carbs": {"type": ["integer", "null"], "minimum": 0},
                    "fiber": {"type": ["integer", "null"], "minimum": 0},
                    "sugar": {"type": ["integer", "null"], "minimum": 0},
                    "sodium": {"type": ["integer", "null"], "minimum": 0},
                    "meal_type": {
                        "type": ["string", "null"],
                        "enum": ["breakfast", "lunch", "dinner", "snack", None],
                    },
                    "consumed_at": {
                        "type": ["string", "null"],
                        "description": "Replacement ISO 8601 date-time with timezone.",
                    },
                    "notes": {"type": ["string", "null"]},
                },
                "required": ["meal_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_meal",
            "description": (
                "Delete one existing meal belonging to the authenticated user. Use only when the user clearly wants that meal removed. "
                "Resolve the exact meal_id with get_meals first; never guess an id."
            ),
            "parameters": {
                "type": "object",
                "properties": {"meal_id": {"type": "integer", "minimum": 1}},
                "required": ["meal_id"],
                "additionalProperties": False,
            },
        },
    },
]

MEAL_MUTATION_TOOL_NAMES = {tool["function"]["name"] for tool in MEAL_MUTATION_TOOLS}


def _safe_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _normalize_datetime(value: Any, timezone_name: str) -> datetime:
    if value in (None, ""):
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ValueError("consumed_at must be an ISO 8601 date-time")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=_safe_zoneinfo(timezone_name))
    return value.astimezone(timezone.utc)


def _clean_description(value: Any) -> str:
    description = str(value or "").strip()
    if not description:
        raise ValueError("food_description is required")
    if len(description) > 2000:
        raise ValueError("food_description is too long")
    return description


def _nutrition_value(name: str, value: Any) -> int:
    if value is None:
        raise ValueError(f"{name} is missing from meal analysis")
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative number")
    number = int(round(float(value)))
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _meal_type(value: Any, *, fallback: str = "snack") -> str:
    normalized = str(value or fallback).strip().lower()
    if normalized not in VALID_MEAL_TYPES:
        raise ValueError("meal_type must be breakfast, lunch, dinner, or snack")
    return normalized


def _meal_payload(meal: models.Meal) -> dict[str, Any]:
    return {
        "id": meal.id,
        "calories": meal.calories,
        "protein": meal.protein,
        "fat": meal.fat,
        "carbs": meal.carbs,
        "fiber": meal.fiber,
        "sugar": meal.sugar,
        "sodium": meal.sodium,
        "meal_type": meal.meal_type,
        "consumed_at": meal.consumed_at.isoformat() if meal.consumed_at else None,
        "notes": meal.notes,
        "text_only": bool(meal.is_text_only),
    }


def _analyze_food(description: str) -> dict[str, Any]:
    try:
        (
            calories,
            protein,
            fat,
            carbs,
            fiber,
            sugar,
            sodium,
            meal_type,
            consumed_at,
            notes,
        ) = get_meal_data_from_text(description)
    except Exception as exc:
        logger.exception("Assistant meal analysis failed")
        raise ValueError("Meal analysis failed; nothing was saved") from exc

    return {
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
        "fiber": fiber,
        "sugar": sugar,
        "sodium": sodium,
        "meal_type": meal_type,
        "consumed_at": consumed_at,
        "notes": notes,
    }


def _build_notes(description: str, user_notes: Any, ai_notes: Any) -> str:
    parts = [f"Text description: {description}"]
    cleaned_notes = str(user_notes or "").strip()
    cleaned_ai = str(ai_notes or "").strip()
    if cleaned_notes:
        parts.append(cleaned_notes)
    if cleaned_ai:
        parts.append(f"AI Analysis: {cleaned_ai}")
    return "\n\n".join(parts)


def _add_meal(db: Session, user: models.User, args: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    description = _clean_description(args.get("food_description"))
    needs_analysis = any(args.get(field) is None for field in NUTRITION_FIELDS) or args.get("meal_type") is None
    analysis = _analyze_food(description) if needs_analysis else {}

    nutrition = {
        field: _nutrition_value(field, args.get(field) if args.get(field) is not None else analysis.get(field))
        for field in NUTRITION_FIELDS
    }
    meal_type = _meal_type(args.get("meal_type") if args.get("meal_type") is not None else analysis.get("meal_type"))
    consumed_source = args.get("consumed_at")
    if consumed_source in (None, ""):
        consumed_source = analysis.get("consumed_at")
    consumed_at = _normalize_datetime(consumed_source, timezone_name)
    notes = _build_notes(description, args.get("notes"), analysis.get("notes"))

    meal = models.Meal(
        user_id=user.id,
        image_path=None,
        calories=nutrition["calories"],
        protein=nutrition["protein"],
        fat=nutrition["fat"],
        carbs=nutrition["carbs"],
        fiber=nutrition["fiber"],
        sugar=nutrition["sugar"],
        sodium=nutrition["sodium"],
        meal_type=meal_type,
        consumed_at=consumed_at,
        notes=notes,
        is_text_only=True,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return {"created": True, "meal": _meal_payload(meal)}


def _get_meal(db: Session, user_id: int, meal_id: Any) -> models.Meal:
    try:
        normalized_id = int(meal_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("meal_id must be an integer") from exc
    meal = db.query(models.Meal).filter(models.Meal.id == normalized_id, models.Meal.user_id == user_id).first()
    if meal is None:
        raise ValueError("Meal not found for the current user")
    return meal


def _update_meal(db: Session, user: models.User, args: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    meal = _get_meal(db, user.id, args.get("meal_id"))
    description_raw = args.get("food_description")
    description = _clean_description(description_raw) if description_raw not in (None, "") else None
    explicit_fields = {
        field for field in (*NUTRITION_FIELDS, "meal_type", "consumed_at", "notes") if field in args and args.get(field) is not None
    }
    if description is None and not explicit_fields:
        raise ValueError("No meal changes were provided")

    if description is not None:
        analysis = _analyze_food(description)
        for field in NUTRITION_FIELDS:
            value = args.get(field) if args.get(field) is not None else analysis.get(field)
            setattr(meal, field, _nutrition_value(field, value))
        meal.notes = _build_notes(description, args.get("notes"), analysis.get("notes"))

    for field in NUTRITION_FIELDS:
        if field in explicit_fields:
            setattr(meal, field, _nutrition_value(field, args.get(field)))
    if "meal_type" in explicit_fields:
        meal.meal_type = _meal_type(args.get("meal_type"))
    if "consumed_at" in explicit_fields:
        meal.consumed_at = _normalize_datetime(args.get("consumed_at"), timezone_name)
    if "notes" in explicit_fields and description is None:
        meal.notes = str(args.get("notes") or "").strip() or None

    db.commit()
    db.refresh(meal)
    return {"updated": True, "meal": _meal_payload(meal)}


def _delete_meal(db: Session, user: models.User, args: dict[str, Any]) -> dict[str, Any]:
    meal = _get_meal(db, user.id, args.get("meal_id"))
    meal_id = meal.id
    image_path = meal.image_path
    db.delete(meal)
    db.commit()

    image_deleted = False
    if image_path:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                image_deleted = True
        except OSError as exc:
            logger.warning("Unable to delete image for assistant-deleted meal %s: %s", meal_id, exc)

    return {"deleted": True, "meal_id": meal_id, "image_deleted": image_deleted}


def execute_meal_mutation_tool(
    db: Session,
    user: models.User,
    tool_name: str,
    args: dict[str, Any],
    *,
    timezone_name: str,
) -> dict[str, Any]:
    try:
        if tool_name == "add_meal":
            return _add_meal(db, user, args, timezone_name)
        if tool_name == "update_meal":
            return _update_meal(db, user, args, timezone_name)
        if tool_name == "delete_meal":
            return _delete_meal(db, user, args)
        return {"error": f"Unknown meal mutation tool: {tool_name}"}
    except ValueError as exc:
        db.rollback()
        return {"error": str(exc)}
    except Exception:
        db.rollback()
        logger.exception("Assistant meal mutation failed: %s", tool_name)
        return {"error": "Meal change failed; no further changes were applied"}
