import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base
from .sql_types import UTCDateTime


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"


class Goal(str, enum.Enum):
    WEIGHT_LOSS = "weight_loss"
    MAINTENANCE = "maintenance"
    MUSCLE_GAIN = "muscle_gain"


class DietaryPreference(str, enum.Enum):
    NONE = "none"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    KETO = "keto"
    HIGH_PROTEIN = "high_protein"
    LOW_CARB = "low_carb"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)

    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)

    activity_level = Column(String, nullable=True, default="sedentary")
    goal = Column(String, nullable=True, default="maintenance")
    dietary_preference = Column(String, nullable=True, default="none")

    custom_calories = Column(Integer, nullable=True)
    custom_protein_g = Column(Integer, nullable=True)
    custom_carbs_g = Column(Integer, nullable=True)
    custom_fats_g = Column(Integer, nullable=True)
    custom_fiber_g = Column(Integer, nullable=True)

    bmr = Column(Float, nullable=True)
    tdee = Column(Float, nullable=True)
    target_calories = Column(Integer, nullable=True)
    target_protein_g = Column(Integer, nullable=True)
    target_carbs_g = Column(Integer, nullable=True)
    target_fats_g = Column(Integer, nullable=True)
    target_fiber_g = Column(Integer, nullable=True)

    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="profile")


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    image_path = Column(String, nullable=True)
    calories = Column(Integer, nullable=False)
    protein = Column(Integer, nullable=True)
    fat = Column(Integer, nullable=True)
    carbs = Column(Integer, nullable=True)
    fiber = Column(Integer, nullable=True)
    sugar = Column(Integer, nullable=True)
    sodium = Column(Integer, nullable=True)
    meal_type = Column(String, nullable=False)
    consumed_at = Column(UTCDateTime(), nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_text_only = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="meals")
