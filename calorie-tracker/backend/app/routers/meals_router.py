import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai_analyzer import get_meal_data_from_image, get_meal_data_from_text
from ..deps import get_current_user, get_db
from ..logger import get_logger, log_exception, log_execution_time
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


def _meal_image_url(user_id: int, image_path: str | None) -> str:
    if not image_path:
        return TEXT_MEAL_PLACEHOLDER
    return f"/uploads/{user_id}/{os.path.basename(image_path)}"


def _meal_to_schema(meal: models.Meal, user_id: int) -> schemas.MealOut:
    return schemas.MealOut(
        id=meal.id,
        calories=meal.calories,
        protein=meal.protein,
        fat=meal.fat,
        carbs=meal.carbs,
        fiber=meal.fiber,
        sugar=meal.sugar,
        sodium=meal.sodium,
        meal_type=meal.meal_type,
        consumed_at=_normalize_datetime(meal.consumed_at),
        notes=meal.notes,
        image_url=_meal_image_url(user_id, meal.image_path),
    )


@router.post("/meals", response_model=schemas.MealOut)
@log_execution_time()
async def create_meal(
    image: UploadFile = File(...),
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
        raise HTTPException(status_code=400, detail="Image file is required")

    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    user_dir = os.path.join(str(settings.upload_dir_path), str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    ext = os.path.splitext(image.filename)[1].lower() or ".jpg"
    path = os.path.join(user_dir, f"{uuid.uuid4()}{ext}")

    with open(path, "wb") as file_handle:
        file_handle.write(contents)

    if any(value is None for value in [calories, protein, fat, carbs, fiber, sugar, sodium, meal_type, consumed_at]):
        try:
            (
                ai_calories,
                ai_protein,
                ai_fat,
                ai_carbs,
                ai_fiber,
                ai_sugar,
                ai_sodium,
                ai_meal_type,
                ai_consumed_at,
                ai_notes,
            ) = get_meal_data_from_image(path)
            calories = calories if calories is not None else ai_calories
            protein = protein if protein is not None else ai_protein
            fat = fat if fat is not None else ai_fat
            carbs = carbs if carbs is not None else ai_carbs
            fiber = fiber if fiber is not None else ai_fiber
            sugar = sugar if sugar is not None else ai_sugar
            sodium = sodium if sodium is not None else ai_sodium
            meal_type = meal_type or ai_meal_type
            consumed_at = consumed_at or ai_consumed_at
            if ai_notes:
                notes = f"{notes}\n\nAI Analysis: {ai_notes}" if notes else f"AI Analysis: {ai_notes}"
        except Exception as exc:
            log_exception(logger, exc, "AI analysis failed for meal image")
            calories = calories if calories is not None else 300
            protein = protein if protein is not None else 0
            fat = fat if fat is not None else 0
            carbs = carbs if carbs is not None else 0
            fiber = fiber if fiber is not None else 0
            sugar = sugar if sugar is not None else 0
            sodium = sodium if sodium is not None else 0
            meal_type = meal_type or "snack"
            consumed_at = consumed_at or datetime.now(timezone.utc)

    meal = models.Meal(
        user_id=user.id,
        image_path=path,
        calories=calories or 0,
        protein=protein,
        fat=fat,
        carbs=carbs,
        fiber=fiber,
        sugar=sugar,
        sodium=sodium,
        meal_type=meal_type or "snack",
        consumed_at=_normalize_datetime(consumed_at),
        notes=notes,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return _meal_to_schema(meal, user.id)


@router.post("/meals/text", response_model=schemas.MealOut)
@log_execution_time()
async def create_text_meal(
    meal_data: schemas.TextMealCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if any(
        value is None
        for value in [
            meal_data.calories,
            meal_data.protein,
            meal_data.fat,
            meal_data.carbs,
            meal_data.fiber,
            meal_data.sugar,
            meal_data.sodium,
            meal_data.meal_type,
            meal_data.consumed_at,
        ]
    ):
        try:
            (
                ai_calories,
                ai_protein,
                ai_fat,
                ai_carbs,
                ai_fiber,
                ai_sugar,
                ai_sodium,
                ai_meal_type,
                ai_consumed_at,
                ai_notes,
            ) = get_meal_data_from_text(meal_data.food_description)
            calories = meal_data.calories if meal_data.calories is not None else ai_calories
            protein = meal_data.protein if meal_data.protein is not None else ai_protein
            fat = meal_data.fat if meal_data.fat is not None else ai_fat
            carbs = meal_data.carbs if meal_data.carbs is not None else ai_carbs
            fiber = meal_data.fiber if meal_data.fiber is not None else ai_fiber
            sugar = meal_data.sugar if meal_data.sugar is not None else ai_sugar
            sodium = meal_data.sodium if meal_data.sodium is not None else ai_sodium
            meal_type = meal_data.meal_type or ai_meal_type
            consumed_at = meal_data.consumed_at or ai_consumed_at
            if ai_notes:
                notes = f"{meal_data.notes}\n\nAI Analysis: {ai_notes}" if meal_data.notes else f"AI Analysis: {ai_notes}"
            else:
                notes = meal_data.notes or f"Text description: {meal_data.food_description}"
        except Exception as exc:
            log_exception(logger, exc, "AI analysis failed for text description")
            calories = meal_data.calories if meal_data.calories is not None else 300
            protein = meal_data.protein if meal_data.protein is not None else 0
            fat = meal_data.fat if meal_data.fat is not None else 0
            carbs = meal_data.carbs if meal_data.carbs is not None else 0
            fiber = meal_data.fiber if meal_data.fiber is not None else 0
            sugar = meal_data.sugar if meal_data.sugar is not None else 0
            sodium = meal_data.sodium if meal_data.sodium is not None else 0
            meal_type = meal_data.meal_type or "snack"
            consumed_at = meal_data.consumed_at or datetime.now(timezone.utc)
            notes = meal_data.notes or f"Text description: {meal_data.food_description}"
    else:
        calories = meal_data.calories
        protein = meal_data.protein
        fat = meal_data.fat
        carbs = meal_data.carbs
        fiber = meal_data.fiber
        sugar = meal_data.sugar
        sodium = meal_data.sodium
        meal_type = meal_data.meal_type
        consumed_at = meal_data.consumed_at
        notes = meal_data.notes or f"Text description: {meal_data.food_description}"

    meal = models.Meal(
        user_id=user.id,
        image_path=None,
        calories=calories or 0,
        protein=protein,
        fat=fat,
        carbs=carbs,
        fiber=fiber,
        sugar=sugar,
        sodium=sodium,
        meal_type=meal_type or "snack",
        consumed_at=_normalize_datetime(consumed_at),
        notes=notes,
        is_text_only=True,
    )
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
        raise HTTPException(status_code=404, detail="Meal not found")
    if meal.is_text_only or not meal.image_path:
        raise HTTPException(status_code=400, detail="Cannot reanalyze a text-only meal. Please use the update endpoint instead.")
    if not os.path.exists(meal.image_path):
        raise HTTPException(status_code=400, detail="Image file not found. Cannot reanalyze.")

    try:
        (
            meal.calories,
            meal.protein,
            meal.fat,
            meal.carbs,
            meal.fiber,
            meal.sugar,
            meal.sodium,
            meal.meal_type,
            _,
            ai_notes,
        ) = get_meal_data_from_image(meal.image_path, payload.corrections)
        correction_text = ", ".join(f"{key}: {value}" for key, value in payload.corrections.items())
        meal.notes = f"Updated AI Analysis: {ai_notes}\n\nReanalysis with corrections: {correction_text}"
        db.commit()
        db.refresh(meal)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error reanalyzing meal: {exc}") from exc

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

    meals = query.order_by(models.Meal.consumed_at.desc()).offset(offset).limit(limit).all()
    return [_meal_to_schema(meal, user.id) for meal in meals]


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
    from_dt = _normalize_datetime(frm)
    to_dt = _normalize_datetime(to)
    if from_dt >= to_dt:
        raise HTTPException(status_code=400, detail="'frm' must be earlier than 'to'")

    meals = db.query(models.Meal).filter(
        models.Meal.user_id == user.id,
        models.Meal.consumed_at >= from_dt,
        models.Meal.consumed_at < to_dt,
    ).all()

    timezone_info = None
    if tz_name:
        try:
            timezone_info = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(status_code=400, detail="Invalid timezone name") from exc

    grouped: dict[datetime.date, dict[str, int]] = defaultdict(lambda: {"total_calories": 0, "meals": 0})
    for meal in meals:
        normalized = _normalize_datetime(meal.consumed_at)
        if timezone_info is not None:
            local_day = normalized.astimezone(timezone_info).date()
        else:
            local_day = (normalized - timedelta(minutes=tz_offset_minutes)).date()
        grouped[local_day]["total_calories"] += meal.calories
        grouped[local_day]["meals"] += 1

    days = [
        schemas.DailySummary(date=day, total_calories=values["total_calories"], meals=values["meals"])
        for day, values in sorted(grouped.items(), key=lambda item: item[0])
    ]
    return schemas.SummaryOut(from_dt=from_dt, to_dt=to_dt, days=days)


@router.delete("/meals/{meal_id}", status_code=204)
@log_execution_time()
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    meal = db.query(models.Meal).filter(models.Meal.id == meal_id, models.Meal.user_id == user.id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    image_path = meal.image_path
    try:
        db.delete(meal)
        db.commit()
    except Exception as exc:
        db.rollback()
        log_exception(logger, exc, f"Error deleting meal: meal_id={meal_id}")
        raise HTTPException(status_code=500, detail="Failed to delete meal") from exc

    try:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
    except OSError as exc:
        logger.warning("Unable to delete image for meal %s: %s", meal_id, exc)

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
        raise HTTPException(status_code=404, detail="Meal not found")

    for key, value in meal_update.model_dump(exclude_unset=True).items():
        setattr(meal, key, _normalize_datetime(value) if key == "consumed_at" and value else value)

    db.commit()
    db.refresh(meal)
    return _meal_to_schema(meal, user.id)
