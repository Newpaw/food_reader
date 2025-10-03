import os, uuid
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..settings import settings
from .. import models, schemas
from ..ai_analyzer import get_meal_data_from_image

router = APIRouter(prefix="/me", tags=["meals"])

@router.post("/meals", response_model=schemas.MealOut)
async def create_meal(
    image: UploadFile = File(...),
    calories: Optional[int] = Form(None),
    protein: Optional[int] = Form(None),
    fat: Optional[int] = Form(None),
    carbs: Optional[int] = Form(None),
    fiber: Optional[int] = Form(None),
    sugar: Optional[int] = Form(None),
    sodium: Optional[int] = Form(None),
    meal_type: Optional[str] = Form(None),
    consumed_at: Optional[datetime] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Save file
    user_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    ext = os.path.splitext(image.filename or "")[1].lower() or ".jpg"
    fname = f"{uuid.uuid4()}{ext}"
    path = os.path.join(user_dir, fname)

    with open(path, "wb") as f:
        f.write(await image.read())

    # Use AI to analyze the image if manual data is not provided
    if (calories is None or protein is None or fat is None or carbs is None or
        fiber is None or sugar is None or sodium is None or
        meal_type is None or consumed_at is None):
        try:
            (ai_calories, ai_protein, ai_fat, ai_carbs, ai_fiber,
             ai_sugar, ai_sodium, ai_meal_type, ai_consumed_at, ai_notes) = get_meal_data_from_image(path)
            
            # Use AI-generated data if not manually provided
            calories = calories or ai_calories
            protein = protein or ai_protein
            fat = fat or ai_fat
            carbs = carbs or ai_carbs
            fiber = fiber or ai_fiber
            sugar = sugar or ai_sugar
            sodium = sodium or ai_sodium
            meal_type = meal_type or ai_meal_type
            consumed_at = consumed_at or ai_consumed_at
            
            # Append AI-generated notes to user notes if available
            if ai_notes:
                if notes:
                    notes = f"{notes}\n\nAI Analysis: {ai_notes}"
                else:
                    notes = f"AI Analysis: {ai_notes}"
        except Exception as e:
            # Log the error but continue with default values if AI analysis fails
            print(f"AI analysis error: {str(e)}")
            calories = calories or 300  # Default value
            protein = protein or 0      # Default value
            fat = fat or 0              # Default value
            carbs = carbs or 0          # Default value
            fiber = fiber or 0          # Default value
            sugar = sugar or 0          # Default value
            sodium = sodium or 0        # Default value
            meal_type = meal_type or "snack"  # Default value
            consumed_at = consumed_at or datetime.utcnow()  # Default to current time

    meal = models.Meal(
        user_id=user.id, image_path=path, calories=calories,
        protein=protein, fat=fat, carbs=carbs, fiber=fiber,
        sugar=sugar, sodium=sodium, meal_type=meal_type,
        consumed_at=consumed_at, notes=notes
    )
    db.add(meal); db.commit(); db.refresh(meal)

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
        consumed_at=meal.consumed_at,
        notes=meal.notes,
        image_url=f"/uploads/{user.id}/{fname}"
    )

@router.get("/meals", response_model=List[schemas.MealOut])
def list_meals(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    frm: str | None = None,
    to: str | None = None,
    limit: int = 50,
    offset: int = 0
):
    q = db.query(models.Meal).filter(models.Meal.user_id == user.id)
    if frm: q = q.filter(models.Meal.consumed_at >= frm)
    if to:  q = q.filter(models.Meal.consumed_at < to)
    q = q.order_by(models.Meal.consumed_at.desc()).offset(offset).limit(limit)
    meals = q.all()
    return [
        schemas.MealOut(
            id=m.id,
            calories=m.calories,
            protein=m.protein,
            fat=m.fat,
            carbs=m.carbs,
            fiber=m.fiber,
            sugar=m.sugar,
            sodium=m.sodium,
            meal_type=m.meal_type,
            consumed_at=m.consumed_at,
            notes=m.notes,
            image_url=f"/uploads/{user.id}/{os.path.basename(m.image_path)}"
        ) for m in meals
    ]

@router.get("/summary", response_model=schemas.SummaryOut)
def summary(
    frm: str,
    to: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    from_dt = datetime.fromisoformat(frm)
    to_dt = datetime.fromisoformat(to)
    rows = db.execute(
        """
        SELECT date(consumed_at) as d, SUM(calories) as total, COUNT(*) as meals
        FROM meals
        WHERE user_id = :uid AND consumed_at >= :f AND consumed_at < :t
        GROUP BY date(consumed_at)
        ORDER BY d
        """, {"uid": user.id, "f": from_dt, "t": to_dt}
    ).fetchall()

    days = [schemas.DailySummary(date=datetime.fromisoformat(r[0]+"T00:00:00"), total_calories=r[1], meals=r[2]) for r in rows]
    return schemas.SummaryOut(from_dt=from_dt, to_dt=to_dt, days=days)