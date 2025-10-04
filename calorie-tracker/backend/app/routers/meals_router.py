import os, uuid, pytz
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..settings import settings
from .. import models, schemas
from ..ai_analyzer import get_meal_data_from_image

def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime strings, handling the 'Z' timezone designator.
    Ensures the returned datetime object preserves timezone information.
    
    Args:
        iso_string: ISO 8601 datetime string, possibly with 'Z' timezone designator
        
    Returns:
        timezone-aware datetime object
    """
    # Handle 'Z' timezone designator (replace with +00:00 which fromisoformat can handle)
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1] + '+00:00'
    
    # Handle milliseconds if present (Python < 3.11 can't handle .000 format in fromisoformat)
    if '.' in iso_string and '+' in iso_string:
        parts = iso_string.split('+')
        datetime_part = parts[0]
        timezone_part = '+' + parts[1]
        
        if '.' in datetime_part:
            datetime_parts = datetime_part.split('.')
            # Ensure milliseconds are exactly 6 digits (microseconds)
            if len(datetime_parts[1]) < 6:
                datetime_parts[1] = datetime_parts[1].ljust(6, '0')
            elif len(datetime_parts[1]) > 6:
                datetime_parts[1] = datetime_parts[1][:6]
            datetime_part = '.'.join(datetime_parts)
        
        iso_string = datetime_part + timezone_part
    
    # If no timezone info is present, assume UTC
    if not ('+' in iso_string or '-' in iso_string[1:]):  # Skip potential negative sign at start
        iso_string += '+00:00'
    
    return datetime.fromisoformat(iso_string)

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
            # Continue with default values if AI analysis fails
            calories = calories or 300  # Default value
            protein = protein or 0      # Default value
            fat = fat or 0              # Default value
            carbs = carbs or 0          # Default value
            fiber = fiber or 0          # Default value
            sugar = sugar or 0          # Default value
            sodium = sodium or 0        # Default value
            meal_type = meal_type or "snack"  # Default value
            # Default to current time in UTC with timezone info
            consumed_at = consumed_at or datetime.now(pytz.UTC)

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
    if frm:
        q = q.filter(models.Meal.consumed_at >= frm)
    if to:
        q = q.filter(models.Meal.consumed_at < to)
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
    try:
        # Use our custom parser that handles 'Z' timezone designator
        from_dt = parse_iso_datetime(frm)
        to_dt = parse_iso_datetime(to)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    from sqlalchemy import text
    
    rows = db.execute(
        text("""
        SELECT date(consumed_at) as d, SUM(calories) as total, COUNT(*) as meals
        FROM meals
        WHERE user_id = :uid AND consumed_at >= :f AND consumed_at < :t
        GROUP BY date(consumed_at)
        ORDER BY d
        """), {"uid": user.id, "f": from_dt, "t": to_dt}
    ).fetchall()

    days = [schemas.DailySummary(date=datetime.fromisoformat(r[0]+"T00:00:00+00:00"), total_calories=r[1], meals=r[2]) for r in rows]
    return schemas.SummaryOut(from_dt=from_dt, to_dt=to_dt, days=days)

@router.delete("/meals/{meal_id}", status_code=204)
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Delete a specific meal by ID"""
    meal = db.query(models.Meal).filter(
        models.Meal.id == meal_id,
        models.Meal.user_id == user.id
    ).first()
    
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    db.delete(meal)
    db.commit()
    
    # Try to delete the image file if it exists
    try:
        if meal.image_path and os.path.exists(meal.image_path):
            os.remove(meal.image_path)
    except Exception as e:
        # Silently continue if image deletion fails
        pass
    
    return None  # 204 No Content response

@router.put("/meals/{meal_id}", response_model=schemas.MealOut)
def update_meal(
    meal_id: int,
    meal_update: schemas.MealUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """Update a specific meal by ID"""
    meal = db.query(models.Meal).filter(
        models.Meal.id == meal_id,
        models.Meal.user_id == user.id
    ).first()
    
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    # Update meal attributes if provided in the request
    update_data = meal_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(meal, key, value)
    
    db.commit()
    db.refresh(meal)
    
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
        image_url=f"/uploads/{user.id}/{os.path.basename(meal.image_path)}"
    )
