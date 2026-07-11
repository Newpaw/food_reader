from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai_analyzer import PROMPT_VERSION, get_meal_data_from_image, get_meal_data_from_text
from ..deps import get_current_user, get_db
from ..image_processing import safe_delete_image, store_private_meal_image
from ..logger import get_logger, log_exception, log_execution_time
from ..media_tokens import create_media_url
from ..settings import settings


router = APIRouter(prefix="/me", tags=["meals"])
logger = get_logger(__name__)
TEXT_MEAL_PLACEHOLDER = "/assets/images/text-meal-placeholder.svg"


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime is required.")
    return value.astimezone(timezone.utc)


def _sanitize_text(value: str | None, *, max_length: int = 4000) -> str | None:
    if not value:
        return None
    translation = str.maketrans({"<": "‹", ">": "›", '"': "”", "'": "’", "\x00": ""})
    cleaned = " ".join(value.translate(translation).split())
    return cleaned[:max_length] or None


def _safe_json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _analysis_for_storage(raw: dict[str, Any] | None, *, description: str | None = None) -> dict[str, Any]:
    raw = raw or {}
    calories = int(raw.get("estimated_calories") or raw.get("calories") or 0)
    calorie_min = int(raw.get("calorie_min") or max(1, round(calories * 0.8))) if calories else None
    calorie_max = int(raw.get("calorie_max") or max(1, round(calories * 1.2))) if calories else None
    assumptions = []
    for item in (raw.get("assumptions") or [])[:6]:
        cleaned = _sanitize_text(str(item), max_length=240)
        if cleaned:
            assumptions.append(cleaned)
    return {
        "food_description": _sanitize_text(str(raw.get("food_description") or description or "Meal"), max_length=240),
        "estimated_calories": calories,
        "calorie_min": calorie_min,
        "calorie_max": calorie_max,
        "confidence": int(raw.get("confidence") or 50),
        "components": raw.get("components") if isinstance(raw.get("components"), list) else [],
        "assumptions": assumptions,
        "clarification_question": _sanitize_text(raw.get("clarification_question"), max_length=240),
        "notes": _sanitize_text(raw.get("notes"), max_length=400),
    }


def _meal_to_schema(meal: models.Meal, user_id: int) -> schemas.MealOut:
    analysis = _safe_json_loads(meal.analysis_json)
    components: list[schemas.MealComponent] = []
    for item in analysis.get("components", [])[:12]:
        if isinstance(item, dict):
            try:
                components.append(schemas.MealComponent.model_validate(item))
            except Exception:
                pass
    image_url = TEXT_MEAL_PLACEHOLDER if not meal.image_path else create_media_url(meal_id=meal.id, user_id=user_id)
    return schemas.MealOut(
        id=meal.id,
        food_description=meal.food_description,
        calories=meal.calories,
        calorie_min=meal.calorie_min,
        calorie_max=meal.calorie_max,
        confidence=meal.confidence,
        protein=meal.protein,
        fat=meal.fat,
        carbs=meal.carbs,
        fiber=meal.fiber,
        sugar=meal.sugar,
        sodium=meal.sodium,
        meal_type=meal.meal_type,
        consumed_at=_normalize_datetime(meal.consumed_at),
        notes=meal.notes,
        components=components,
        assumptions=[str(item) for item in analysis.get("assumptions", [])[:6]],
        clarification_question=analysis.get("clarification_question"),
        image_url=image_url,
    )


def _snapshot(meal: models.Meal) -> dict[str, Any]:
    return {
        "calories": meal.calories,
        "protein": meal.protein,
        "fat": meal.fat,
        "carbs": meal.carbs,
        "fiber": meal.fiber,
        "sugar": meal.sugar,
        "sodium": meal.sodium,
        "meal_type": meal.meal_type,
        "consumed_at": _normalize_datetime(meal.consumed_at).isoformat(),
        "notes": meal.notes,
    }


def _record_correction(db: Session, *, user_id: int, meal_id: int, before: dict[str, Any], after: dict[str, Any], reason: str | None) -> None:
    if before == after:
        return
    db.add(
        models.MealCorrection(
            user_id=user_id,
            meal_id=meal_id,
            before_json=json.dumps(before, ensure_ascii=False),
            after_json=json.dumps(after, ensure_ascii=False),
            reason=_sanitize_text(reason, max_length=500),
        )
    )


def _recent_correction_examples(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(models.MealCorrection)
        .filter(models.MealCorrection.user_id == user_id)
        .order_by(models.MealCorrection.created_at.desc())
        .limit(5)
        .all()
    )
    examples: list[str] = []
    for row in rows:
        try:
            before, after = json.loads(row.before_json), json.loads(row.after_json)
        except (json.JSONDecodeError, TypeError):
            continue
        examples.append(
            f"Estimate corrected from {before.get('calories', '?')} to {after.get('calories', '?')} kcal; "
            f"protein {before.get('protein', '?')} to {after.get('protein', '?')} g"
            + (f"; reason: {row.reason}" if row.reason else "")
        )
    return examples


def _analysis_from_result(result: Any, *, description: str | None = None) -> dict[str, Any]:
    return _analysis_for_storage(getattr(result, "analysis", None), description=description)


def _apply_analysis_metadata(meal: models.Meal, analysis: dict[str, Any]) -> None:
    meal.food_description = analysis.get("food_description")
    meal.calorie_min = analysis.get("calorie_min")
    meal.calorie_max = analysis.get("calorie_max")
    meal.confidence = analysis.get("confidence")
    meal.analysis_json = json.dumps(analysis, ensure_ascii=False)
    meal.analysis_model = settings.LLM_MODEL
    meal.prompt_version = PROMPT_VERSION


@router.post("/meals", response_model=schemas.MealOut)
@log_execution_time()
async def create_meal(
    image: UploadFile = File(...),
    analysis_context: str | None = Form(None),
    calories: int | None = Form(None),
    protein: int | None = Form(None),
    fat: int | None = Form(None),
    carbs: int | None = Form(None),
    fiber: int | None = Form(None),
    sugar: int | None = Form(None),
    sodium: int | None = Form(None),
    meal_type: str | None = Form(None),
    consumed_at: AwareDatetime | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if not image.filename:
        raise HTTPException(status_code=400, detail="Image file is required.")
    path = await store_private_meal_image(image, user.id)
    cleaned_context = _sanitize_text(analysis_context, max_length=2000)
    analysis: dict[str, Any] = {}
    try:
        if any(value is None for value in [calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, consumed_at]):
            kwargs: dict[str, Any] = {"analysis_context": cleaned_context}
            examples = _recent_correction_examples(db, user.id)
            if examples:
                kwargs["correction_examples"] = examples
            result = await run_in_threadpool(get_meal_data_from_image, path, **kwargs)
            ai_calories, ai_protein, ai_fat, ai_carbs, ai_fiber, ai_sugar, ai_sodium, ai_type, ai_time, ai_description = result
            analysis = _analysis_from_result(result, description=ai_description)
            calories = ai_calories if calories is None else calories
            protein = ai_protein if protein is None else protein
            fat = ai_fat if fat is None else fat
            carbs = ai_carbs if carbs is None else carbs
            fiber = ai_fiber if fiber is None else fiber
            sugar = ai_sugar if sugar is None else sugar
            sodium = ai_sodium if sodium is None else sodium
            meal_type = meal_type or ai_type
            consumed_at = consumed_at or ai_time
            analysis["user_context"] = cleaned_context
            if not notes:
                lines = [f"AI Analysis: {analysis.get('notes') or ai_description}"]
                if cleaned_context:
                    lines.append(f"User context: {cleaned_context}")
                notes = "\n".join(lines)
        else:
            analysis = _analysis_for_storage({"food_description": notes or cleaned_context or "Meal", "estimated_calories": calories, "confidence": 100})

        meal = models.Meal(
            user_id=user.id,
            image_path=path,
            calories=max(int(calories or 0), 0),
            protein=max(int(protein or 0), 0),
            fat=max(int(fat or 0), 0),
            carbs=max(int(carbs or 0), 0),
            fiber=max(int(fiber or 0), 0),
            sugar=max(int(sugar or 0), 0),
            sodium=max(int(sodium or 0), 0),
            meal_type=meal_type if meal_type in {"breakfast", "lunch", "dinner", "snack"} else "snack",
            consumed_at=_normalize_datetime(consumed_at),
            notes=_sanitize_text(notes),
            confirmed_at=datetime.now(timezone.utc),
        )
        _apply_analysis_metadata(meal, analysis)
        db.add(meal)
        db.commit()
        db.refresh(meal)
        return _meal_to_schema(meal, user.id)
    except HTTPException:
        safe_delete_image(path)
        raise
    except Exception as exc:
        db.rollback()
        safe_delete_image(path)
        log_exception(logger, exc, "Unable to create image meal")
        raise HTTPException(status_code=500, detail="Unable to create the meal.") from exc


@router.post("/meals/text", response_model=schemas.MealOut)
@log_execution_time()
async def create_text_meal(
    meal_data: schemas.TextMealCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    description = _sanitize_text(meal_data.food_description, max_length=2000) or "Meal"
    analysis: dict[str, Any]
    if any(value is None for value in [meal_data.calories, meal_data.protein, meal_data.fat, meal_data.carbs, meal_data.fiber, meal_data.sugar, meal_data.sodium, meal_data.meal_type, meal_data.consumed_at]):
        examples = _recent_correction_examples(db, user.id)
        result = await run_in_threadpool(get_meal_data_from_text, description, correction_examples=examples) if examples else await run_in_threadpool(get_meal_data_from_text, description)
        ai_calories, ai_protein, ai_fat, ai_carbs, ai_fiber, ai_sugar, ai_sodium, ai_type, ai_time, ai_description = result
        analysis = _analysis_from_result(result, description=ai_description or description)
        calories = ai_calories if meal_data.calories is None else meal_data.calories
        protein = ai_protein if meal_data.protein is None else meal_data.protein
        fat = ai_fat if meal_data.fat is None else meal_data.fat
        carbs = ai_carbs if meal_data.carbs is None else meal_data.carbs
        fiber = ai_fiber if meal_data.fiber is None else meal_data.fiber
        sugar = ai_sugar if meal_data.sugar is None else meal_data.sugar
        sodium = ai_sodium if meal_data.sodium is None else meal_data.sodium
        meal_type = meal_data.meal_type or ai_type
        consumed_at = meal_data.consumed_at or ai_time
        notes = meal_data.notes or analysis.get("notes") or ai_description
    else:
        calories, protein, fat, carbs = meal_data.calories, meal_data.protein, meal_data.fat, meal_data.carbs
        fiber, sugar, sodium = meal_data.fiber, meal_data.sugar, meal_data.sodium
        meal_type, consumed_at = meal_data.meal_type, meal_data.consumed_at
        notes = meal_data.notes or description
        analysis = _analysis_for_storage({"food_description": description, "estimated_calories": calories, "confidence": 100})

    meal = models.Meal(
        user_id=user.id,
        image_path=None,
        calories=max(int(calories or 0), 0),
        protein=max(int(protein or 0), 0),
        fat=max(int(fat or 0), 0),
        carbs=max(int(carbs or 0), 0),
        fiber=max(int(fiber or 0), 0),
        sugar=max(int(sugar or 0), 0),
        sodium=max(int(sodium or 0), 0),
        meal_type=meal_type if meal_type in {"breakfast", "lunch", "dinner", "snack"} else "snack",
        consumed_at=_normalize_datetime(consumed_at),
        notes=_sanitize_text(notes),
        is_text_only=True,
        confirmed_at=datetime.now(timezone.utc),
    )
    _apply_analysis_metadata(meal, analysis)
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return _meal_to_schema(meal, user.id)


@router.post("/meals/{meal_id}/reanalyze", response_model=schemas.MealOut)
@log_execution_time()
async def reanalyze_meal(
    meal_id: int,
    payload: schemas.MealReanalysis,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    meal = db.query(models.Meal).filter(models.Meal.id == meal_id, models.Meal.user_id == user.id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found.")
    if meal.is_text_only or not meal.image_path:
        raise HTTPException(status_code=400, detail="Only photo meals can be reanalyzed.")
    if not os.path.exists(meal.image_path):
        raise HTTPException(status_code=400, detail="Meal image is unavailable.")
    refinement = payload.refinement_context
    if not refinement and payload.corrections:
        refinement = "; ".join(str(value) for value in payload.corrections.values() if value)
    refinement = _sanitize_text(refinement, max_length=2000)
    if not refinement:
        raise HTTPException(status_code=400, detail="Refinement context is required.")

    before = _snapshot(meal)
    try:
        kwargs: dict[str, Any] = {"refinement_context": refinement}
        examples = _recent_correction_examples(db, user.id)
        if examples:
            kwargs["correction_examples"] = examples
        result = await run_in_threadpool(get_meal_data_from_image, meal.image_path, **kwargs)
        meal.calories, meal.protein, meal.fat, meal.carbs, meal.fiber, meal.sugar, meal.sodium, meal.meal_type, _, description = result
        previous = _safe_json_loads(meal.analysis_json)
        original_context = previous.get("user_context")
        analysis = _analysis_from_result(result, description=description)
        analysis["user_context"] = original_context
        analysis["refinement_context"] = refinement
        lines = [f"Updated AI Analysis: {analysis.get('notes') or description}"]
        if original_context:
            lines.append(f"Original user context: {original_context}")
        lines.append(f"Refinement context: {refinement}")
        meal.notes = _sanitize_text("\n".join(lines))
        _apply_analysis_metadata(meal, analysis)
        _record_correction(db, user_id=user.id, meal_id=meal.id, before=before, after=_snapshot(meal), reason=refinement)
        db.commit()
        db.refresh(meal)
    except Exception as exc:
        db.rollback()
        log_exception(logger, exc, f"Meal reanalysis failed: meal_id={meal_id}")
        raise HTTPException(status_code=500, detail="Unable to reanalyze the meal.") from exc
    return _meal_to_schema(meal, user.id)


@router.get("/meals", response_model=list[schemas.MealOut])
@log_execution_time(level=logging.INFO)
def list_meals(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    frm: AwareDatetime | None = Query(None),
    to: AwareDatetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(models.Meal).filter(models.Meal.user_id == user.id)
    if frm:
        query = query.filter(models.Meal.consumed_at >= _normalize_datetime(frm))
    if to:
        query = query.filter(models.Meal.consumed_at < _normalize_datetime(to))
    return [_meal_to_schema(meal, user.id) for meal in query.order_by(models.Meal.consumed_at.desc()).offset(offset).limit(limit).all()]


@router.get("/summary", response_model=schemas.SummaryOut)
@log_execution_time(level=logging.INFO)
def summary(
    frm: AwareDatetime,
    to: AwareDatetime,
    tz_name: str | None = Query(None, min_length=1, max_length=64),
    tz_offset_minutes: int = Query(0, ge=-840, le=840),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    from_dt, to_dt = _normalize_datetime(frm), _normalize_datetime(to)
    if from_dt >= to_dt:
        raise HTTPException(status_code=400, detail="'frm' must be earlier than 'to'.")
    meals = db.query(models.Meal).filter(models.Meal.user_id == user.id, models.Meal.consumed_at >= from_dt, models.Meal.consumed_at < to_dt).all()
    timezone_info = None
    if tz_name:
        try:
            timezone_info = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(status_code=400, detail="Invalid timezone name.") from exc
    grouped = defaultdict(lambda: {"total_calories": 0, "meals": 0})
    for meal in meals:
        normalized = _normalize_datetime(meal.consumed_at)
        local_day = normalized.astimezone(timezone_info).date() if timezone_info else (normalized - timedelta(minutes=tz_offset_minutes)).date()
        grouped[local_day]["total_calories"] += meal.calories
        grouped[local_day]["meals"] += 1
    days = [schemas.DailySummary(date=day, total_calories=value["total_calories"], meals=value["meals"]) for day, value in sorted(grouped.items())]
    return schemas.SummaryOut(from_dt=from_dt, to_dt=to_dt, days=days)


@router.delete("/meals/{meal_id}", status_code=204)
@log_execution_time()
def delete_meal(meal_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    meal = db.query(models.Meal).filter(models.Meal.id == meal_id, models.Meal.user_id == user.id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found.")
    image_path = meal.image_path
    try:
        db.delete(meal)
        db.commit()
    except Exception as exc:
        db.rollback()
        log_exception(logger, exc, f"Error deleting meal: meal_id={meal_id}")
        raise HTTPException(status_code=500, detail="Failed to delete the meal.") from exc
    safe_delete_image(image_path)
    return Response(status_code=204)


@router.put("/meals/{meal_id}", response_model=schemas.MealOut)
def update_meal(
    meal_id: int,
    meal_update: schemas.MealUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    meal = db.query(models.Meal).filter(models.Meal.id == meal_id, models.Meal.user_id == user.id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found.")
    before = _snapshot(meal)
    update_data = meal_update.model_dump(exclude_unset=True)
    reason = update_data.pop("correction_reason", None)
    for key, value in update_data.items():
        if key == "consumed_at" and value:
            value = _normalize_datetime(value)
        elif key == "notes":
            value = _sanitize_text(value)
        setattr(meal, key, value)
    meal.confirmed_at = meal.confirmed_at or datetime.now(timezone.utc)
    _record_correction(db, user_id=user.id, meal_id=meal.id, before=before, after=_snapshot(meal), reason=reason or "Manual review")
    db.commit()
    db.refresh(meal)
    return _meal_to_schema(meal, user.id)
