from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..deps import get_current_user, get_db


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=schemas.UserProfileOut)
async def get_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = crud.get_user_profile(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create a profile first.",
        )
    return profile


@router.post("", response_model=schemas.UserProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: schemas.UserProfileCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_profile = crud.get_user_profile(db, current_user.id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT to update.",
        )

    return crud.create_user_profile(db, current_user.id, profile_data)


@router.put("", response_model=schemas.UserProfileOut)
async def update_profile(
    profile_data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = crud.update_user_profile(db, current_user.id, profile_data)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create a profile first.",
        )
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success = crud.delete_user_profile(db, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return None


@router.get("/targets", response_model=schemas.NutritionTargets | None)
async def get_nutrition_targets(
    timezone_name: str = Query("UTC", alias="timezone"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_nutrition_targets(db, current_user.id, timezone_name=timezone_name)


@router.get("/activity-levels")
async def get_activity_levels():
    from ..nutrition_calculator import NutritionCalculator

    return {
        "sedentary": NutritionCalculator.get_activity_level_description("sedentary"),
        "lightly_active": NutritionCalculator.get_activity_level_description("lightly_active"),
        "moderately_active": NutritionCalculator.get_activity_level_description("moderately_active"),
        "very_active": NutritionCalculator.get_activity_level_description("very_active"),
        "extremely_active": NutritionCalculator.get_activity_level_description("extremely_active"),
    }


@router.get("/goals")
async def get_goals():
    from ..nutrition_calculator import NutritionCalculator

    return {
        "weight_loss": NutritionCalculator.get_goal_description("weight_loss"),
        "maintenance": NutritionCalculator.get_goal_description("maintenance"),
        "muscle_gain": NutritionCalculator.get_goal_description("muscle_gain"),
    }


@router.get("/dietary-preferences")
async def get_dietary_preferences():
    from ..nutrition_calculator import NutritionCalculator

    preferences = {}
    for pref, (protein_pct, carbs_pct, fat_pct) in NutritionCalculator.MACRO_DISTRIBUTIONS.items():
        preferences[pref] = {
            "name": pref.replace("_", " ").title(),
            "protein_percent": int(protein_pct * 100),
            "carbs_percent": int(carbs_pct * 100),
            "fat_percent": int(fat_pct * 100),
        }
    return preferences
