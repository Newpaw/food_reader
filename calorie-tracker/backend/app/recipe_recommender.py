import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import models
from .ai_analyzer import get_openai_client
from .health_service import build_health_summary
from .settings import settings


SYSTEM_PROMPT = """
You are the recipe planner inside Food Reader.
You receive one authenticated user's deterministic nutrition targets, everything logged today, current local time, and optional Oura activity/recovery data.
Your job is to propose one practical recipe for the next meal that fits the remaining day as well as possible.

Rules:
- Treat the supplied targets and logged totals as the source of truth. Never invent foods the user already ate.
- Use the remaining calories, protein, carbs, fat, and fiber as planning constraints, not as exact physiology.
- If Oura data is present, use activity, workouts, readiness, and sleep only to refine meal size and style. Never diagnose from wearable data.
- Respect the user's dietary preference when present.
- Prefer normal food and realistic portions. Do not recommend supplements, fasting, purging, or extreme restriction.
- The recipe is for one person and one next meal. If it is early in the day, leave reasonable room for later food instead of consuming the entire remaining budget.
- If calories are already near/over target but protein or fiber still has a meaningful gap, prefer a smaller lean/high-protein or fiber-rich meal rather than an oversized meal.
- Ingredient amounts and nutrition are estimates; keep them internally plausible.
- Do not include medical claims or generic motivational filler.

Return only minified JSON with exactly these keys:
title, why, prep_minutes, cook_minutes, ingredients, steps, macros, confidence

Schema requirements:
- title: short recipe name
- why: one short sentence explaining why it fits the remaining day
- prep_minutes and cook_minutes: non-negative integers
- ingredients: array of 3 to 10 objects, each with exactly item and amount strings
- steps: array of 2 to 6 short instruction strings
- macros: object with exactly calories, protein_g, carbs_g, fat_g, fiber_g as non-negative integers
- confidence: one of low, medium, high
""".strip()


def _safe_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _number(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _remaining(target: Any, consumed: Any) -> int | None:
    target_number = _number(target)
    consumed_number = _number(consumed) or 0
    if target_number is None:
        return None
    return target_number - consumed_number


def _build_context(
    db: Session,
    user: models.User,
    *,
    timezone_name: str,
) -> dict[str, Any]:
    timezone_info = _safe_zoneinfo(timezone_name)
    now_local = datetime.now(timezone_info)
    today = now_local.date()
    summary = build_health_summary(
        db,
        user.id,
        start_date=today,
        end_date=today,
        timezone_name=timezone_name,
        locale="cs",
    )
    row = (summary.get("days") or [{}])[0]
    nutrition = row.get("nutrition") or {}
    oura = row.get("oura") or None
    targets = summary.get("targets") or None

    consumed = {
        "calories": _number(nutrition.get("calories")) or 0,
        "protein_g": _number(nutrition.get("protein_g")) or 0,
        "carbs_g": _number(nutrition.get("carbs_g")) or 0,
        "fat_g": _number(nutrition.get("fat_g")) or 0,
        "fiber_g": _number(nutrition.get("fiber_g")) or 0,
    }
    remaining = None
    if targets:
        remaining = {
            "calories": _remaining(targets.get("calories"), consumed["calories"]),
            "protein_g": _remaining(targets.get("protein_g"), consumed["protein_g"]),
            "carbs_g": _remaining(targets.get("carbs_g"), consumed["carbs_g"]),
            "fat_g": _remaining(targets.get("fat_g"), consumed["fat_g"]),
            "fiber_g": _remaining(targets.get("fiber_g"), consumed["fiber_g"]),
        }

    oura_context = None
    if oura:
        oura_context = {
            "steps": _number(oura.get("steps")),
            "active_calories": _number(oura.get("active_calories")),
            "total_calories": _number(oura.get("total_calories")),
            "readiness_score": _number(oura.get("readiness_score")),
            "sleep_score": _number(oura.get("sleep_score")),
            "workout_count": _number(oura.get("workout_count")),
            "workout_calories": _number(oura.get("workout_calories")),
            "workout_seconds": _number(oura.get("workout_seconds")),
        }

    return {
        "day": today.isoformat(),
        "now_local": now_local.isoformat(timespec="minutes"),
        "timezone": timezone_name,
        "meal_count": _number(nutrition.get("meal_count")) or 0,
        "consumed": consumed,
        "targets": None
        if not targets
        else {
            "calories": _number(targets.get("calories")),
            "protein_g": _number(targets.get("protein_g")),
            "carbs_g": _number(targets.get("carbs_g")),
            "fat_g": _number(targets.get("fat_g")),
            "fiber_g": _number(targets.get("fiber_g")),
            "goal": targets.get("goal"),
            "dietary_preference": targets.get("dietary_preference"),
        },
        "remaining": remaining,
        "oura": oura_context,
    }


def _fallback(locale: str, message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "message": message,
        "generated_at": datetime.now().astimezone().isoformat(timespec="minutes"),
        "context": context,
        "recipe": None,
    }


def _normalized_recipe(payload: dict[str, Any]) -> dict[str, Any]:
    ingredients = payload.get("ingredients") if isinstance(payload.get("ingredients"), list) else []
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    macros = payload.get("macros") if isinstance(payload.get("macros"), dict) else {}
    confidence = payload.get("confidence") if payload.get("confidence") in {"low", "medium", "high"} else "low"

    normalized_ingredients = []
    for ingredient in ingredients[:10]:
        if not isinstance(ingredient, dict):
            continue
        item = str(ingredient.get("item") or "").strip()
        amount = str(ingredient.get("amount") or "").strip()
        if item and amount:
            normalized_ingredients.append({"item": item[:120], "amount": amount[:80]})

    normalized_steps = [str(step).strip()[:240] for step in steps[:6] if str(step).strip()]
    normalized_macros = {
        key: max(0, _number(macros.get(key)) or 0)
        for key in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")
    }

    return {
        "title": str(payload.get("title") or "Recipe")[:120],
        "why": str(payload.get("why") or "")[:280],
        "prep_minutes": max(0, _number(payload.get("prep_minutes")) or 0),
        "cook_minutes": max(0, _number(payload.get("cook_minutes")) or 0),
        "ingredients": normalized_ingredients,
        "steps": normalized_steps,
        "macros": normalized_macros,
        "confidence": confidence,
    }


def generate_recipe_recommendation(
    db: Session,
    user: models.User,
    *,
    timezone_name: str,
    locale: str = "cs",
) -> dict[str, Any]:
    context = _build_context(db, user, timezone_name=timezone_name)

    if not context.get("targets"):
        return _fallback(
            locale,
            "Nejdřív nastav svůj profil a denní cíle." if locale == "cs" else "Set up your profile and daily targets first.",
            context=context,
        )

    if context.get("meal_count", 0) <= 0:
        return _fallback(
            locale,
            "Nejdřív zapiš, co jsi dnes už jedl. Pak bude recept vycházet ze skutečného zbytku dne."
            if locale == "cs"
            else "Log what you have already eaten today first, so the recipe can use the real remaining day.",
            context=context,
        )

    remaining = context.get("remaining") or {}
    calorie_gap = _number(remaining.get("calories")) or 0
    protein_gap = _number(remaining.get("protein_g")) or 0
    fiber_gap = _number(remaining.get("fiber_g")) or 0
    if calorie_gap <= 100 and protein_gap <= 10 and fiber_gap <= 5:
        return _fallback(
            locale,
            "Podle dnešních záznamů už další plnohodnotný recept k dosažení cílů nepotřebuješ."
            if locale == "cs"
            else "Based on today's log, you do not need another full meal to reach your targets.",
            context=context,
        )

    client = get_openai_client()
    if client is None:
        return _fallback(
            locale,
            "AI recept je teď nedostupný." if locale == "cs" else "AI recipe generation is currently unavailable.",
            context=context,
        )

    language = "Czech" if locale == "cs" else "English"
    prompt = (
        f"Respond in {language}. Generate the single best next-meal recipe for the remaining day. "
        "Use current local time to decide whether to leave room for later meals. "
        "If Oura is absent, simply ignore wearable activity rather than guessing it.\n"
        f"DATA={json.dumps(context, ensure_ascii=False, separators=(',', ':'))}"
    )

    try:
        model = settings.health_coach_model
        completion_options: dict[str, Any] = {"max_completion_tokens": 1200}
        if model.startswith("gpt-5.6"):
            completion_options["reasoning_effort"] = "low"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            **completion_options,
        )
        raw = response.choices[0].message.content or "{}"
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Recipe model returned invalid JSON")
        recipe = _normalized_recipe(json.loads(raw[start : end + 1]))
        if len(recipe["ingredients"]) < 2 or len(recipe["steps"]) < 1:
            raise ValueError("Recipe model returned incomplete recipe")
        return {
            "available": True,
            "message": None,
            "generated_at": datetime.now(_safe_zoneinfo(timezone_name)).isoformat(timespec="minutes"),
            "context": context,
            "recipe": recipe,
        }
    except Exception:
        return _fallback(
            locale,
            "Recept se nepodařilo vygenerovat. Zkus to prosím znovu."
            if locale == "cs"
            else "The recipe could not be generated. Please try again.",
            context=context,
        )
