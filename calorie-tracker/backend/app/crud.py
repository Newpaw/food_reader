from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models, schemas
from .auth import hash_password, verify_password
from .nutrition_calculator import NutritionCalculator


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, email: str, name: str, password: str) -> models.User:
    user = models.User(email=email, name=name, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = get_user_by_email(db, email)
    if user and verify_password(password, user.password_hash):
        return user
    return None


def get_user_profile(db: Session, user_id: int) -> models.UserProfile | None:
    return db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()


def _calculate_profile_targets(profile_data: schemas.UserProfileBase | models.UserProfile) -> dict:
    if not all([
        profile_data.height_cm,
        profile_data.weight_kg,
        profile_data.age,
        profile_data.gender,
    ]):
        return {}

    return NutritionCalculator.calculate_all_targets(
        weight_kg=profile_data.weight_kg,
        height_cm=profile_data.height_cm,
        age=profile_data.age,
        gender=profile_data.gender,
        activity_level=profile_data.activity_level or "sedentary",
        goal=profile_data.goal or "maintenance",
        dietary_preference=profile_data.dietary_preference or "none",
        custom_calories=profile_data.custom_calories,
        custom_protein_g=profile_data.custom_protein_g,
        custom_carbs_g=profile_data.custom_carbs_g,
        custom_fats_g=profile_data.custom_fats_g,
        custom_fiber_g=profile_data.custom_fiber_g,
    )


def _apply_targets(profile: models.UserProfile, targets: dict) -> None:
    profile.bmr = targets.get("bmr")
    profile.tdee = targets.get("tdee")
    profile.target_calories = targets.get("target_calories")
    profile.target_protein_g = targets.get("target_protein_g")
    profile.target_carbs_g = targets.get("target_carbs_g")
    profile.target_fats_g = targets.get("target_fats_g")
    profile.target_fiber_g = targets.get("target_fiber_g")


def create_user_profile(
    db: Session,
    user_id: int,
    profile_data: schemas.UserProfileCreate,
) -> models.UserProfile:
    targets = _calculate_profile_targets(profile_data)

    profile = models.UserProfile(
        user_id=user_id,
        height_cm=profile_data.height_cm,
        weight_kg=profile_data.weight_kg,
        age=profile_data.age,
        gender=profile_data.gender,
        activity_level=profile_data.activity_level or "sedentary",
        goal=profile_data.goal or "maintenance",
        dietary_preference=profile_data.dietary_preference or "none",
        custom_calories=profile_data.custom_calories,
        custom_protein_g=profile_data.custom_protein_g,
        custom_carbs_g=profile_data.custom_carbs_g,
        custom_fats_g=profile_data.custom_fats_g,
        custom_fiber_g=profile_data.custom_fiber_g,
        adaptive_calories_enabled=profile_data.adaptive_calories_enabled,
        weight_source="manual" if profile_data.weight_kg is not None else None,
    )
    _apply_targets(profile, targets)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    if profile.adaptive_calories_enabled:
        from .adaptive_targets import refresh_adaptive_target

        refresh_adaptive_target(db, user_id)
        db.refresh(profile)
    return profile


def update_user_profile(
    db: Session,
    user_id: int,
    profile_data: schemas.UserProfileUpdate,
) -> models.UserProfile | None:
    profile = get_user_profile(db, user_id)
    if not profile:
        return None

    previous_target = profile.target_calories
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    if "weight_kg" in update_data:
        profile.weight_source = "manual" if update_data["weight_kg"] is not None else None
        profile.weight_measured_at = None

    _apply_targets(profile, _calculate_profile_targets(profile))
    if (
        not profile.adaptive_calories_enabled
        or profile.custom_calories is not None
        or profile.target_calories != previous_target
    ):
        profile.adaptive_target_calories = None
        profile.adaptive_target_updated_on = None
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    if profile.adaptive_calories_enabled:
        from .adaptive_targets import refresh_adaptive_target

        refresh_adaptive_target(db, user_id)
        db.refresh(profile)
    return profile


def delete_user_profile(db: Session, user_id: int) -> bool:
    profile = get_user_profile(db, user_id)
    if not profile:
        return False

    db.delete(profile)
    db.commit()
    return True


def apply_withings_profile_weight(
    db: Session,
    user_id: int,
    weight_kg: float,
    measured_at: datetime,
) -> models.UserProfile | None:
    profile = get_user_profile(db, user_id)
    if not profile:
        return None

    profile.weight_kg = weight_kg
    profile.weight_source = "withings"
    profile.weight_measured_at = measured_at.astimezone(timezone.utc)
    _apply_targets(profile, _calculate_profile_targets(profile))
    profile.adaptive_target_calories = None
    profile.adaptive_target_updated_on = None
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    if profile.adaptive_calories_enabled:
        from .adaptive_targets import refresh_adaptive_target

        refresh_adaptive_target(db, user_id)
        db.refresh(profile)
    return profile


def get_nutrition_targets(
    db: Session,
    user_id: int,
    *,
    timezone_name: str = "UTC",
) -> schemas.NutritionTargets | None:
    from .adaptive_targets import resolve_nutrition_targets

    return resolve_nutrition_targets(db, user_id, timezone_name=timezone_name)
