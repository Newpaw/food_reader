import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base
from .sql_types import UTCDateTime


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"


class FitnessGoal(str, enum.Enum):
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
    daily_checkins = relationship("DailyCheckin", back_populates="user", cascade="all, delete-orphan")
    meal_corrections = relationship("MealCorrection", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    withings_connection = relationship(
        "WithingsConnection",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    withings_measurements = relationship(
        "WithingsMeasurement",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)

    activity_level = Column(String, nullable=True, default="sedentary")
    goal = Column(String, nullable=True, default="weight_loss")
    dietary_preference = Column(String, nullable=True, default="none")

    custom_calories = Column(Integer, nullable=True)
    custom_protein_g = Column(Integer, nullable=True)
    custom_carbs_g = Column(Integer, nullable=True)
    custom_fats_g = Column(Integer, nullable=True)
    custom_fiber_g = Column(Integer, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    desired_weekly_loss_percent = Column(Float, nullable=True, default=0.6)

    bmr = Column(Float, nullable=True)
    tdee = Column(Float, nullable=True)
    target_calories = Column(Integer, nullable=True)
    target_protein_g = Column(Integer, nullable=True)
    target_carbs_g = Column(Integer, nullable=True)
    target_fats_g = Column(Integer, nullable=True)
    target_fiber_g = Column(Integer, nullable=True)
    weight_source = Column(String, nullable=True, default="manual")
    weight_measured_at = Column(UTCDateTime(), nullable=True)

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
    food_description = Column(String, nullable=True)
    calories = Column(Integer, nullable=False)
    calorie_min = Column(Integer, nullable=True)
    calorie_max = Column(Integer, nullable=True)
    confidence = Column(Integer, nullable=True)
    protein = Column(Integer, nullable=True)
    fat = Column(Integer, nullable=True)
    carbs = Column(Integer, nullable=True)
    fiber = Column(Integer, nullable=True)
    sugar = Column(Integer, nullable=True)
    sodium = Column(Integer, nullable=True)
    meal_type = Column(String, nullable=False)
    consumed_at = Column(UTCDateTime(), nullable=False)
    notes = Column(Text, nullable=True)
    analysis_json = Column(Text, nullable=True)
    analysis_model = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    confirmed_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=True)
    is_text_only = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="meals")
    corrections = relationship("MealCorrection", back_populates="meal", cascade="all, delete-orphan")


class MealCorrection(Base):
    __tablename__ = "meal_corrections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    meal_id = Column(Integer, ForeignKey("meals.id"), index=True, nullable=False)
    before_json = Column(Text, nullable=False)
    after_json = Column(Text, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="meal_corrections")
    meal = relationship("Meal", back_populates="corrections")


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkin_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    checkin_date = Column(String, nullable=False)
    hunger = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    steps = Column(Integer, nullable=True)
    trained = Column(Boolean, default=False, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="daily_checkins")


class WithingsConnection(Base):
    __tablename__ = "withings_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    withings_user_id = Column(String, nullable=True)
    access_token_encrypted = Column(String, nullable=False)
    refresh_token_encrypted = Column(String, nullable=False)
    scope = Column(String, nullable=True)
    token_expires_at = Column(UTCDateTime(), nullable=True)
    last_sync_at = Column(UTCDateTime(), nullable=True)
    last_update_timestamp = Column(Integer, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="withings_connection")


class WithingsMeasurement(Base):
    __tablename__ = "withings_measurements"
    __table_args__ = (UniqueConstraint("user_id", "withings_grpid", name="uq_withings_measurements_user_grpid"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    withings_grpid = Column(String, nullable=False)
    measured_at = Column(UTCDateTime(), index=True, nullable=False)
    remote_created_at = Column(UTCDateTime(), nullable=True)
    remote_modified_at = Column(UTCDateTime(), nullable=True)
    attrib = Column(Integer, nullable=True)
    category = Column(Integer, nullable=True)
    device_id = Column(String, nullable=True)
    model = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=True)
    fat_free_mass_kg = Column(Float, nullable=True)
    fat_ratio = Column(Float, nullable=True)
    fat_mass_kg = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    hydration_kg = Column(Float, nullable=True)
    bone_mass_kg = Column(Float, nullable=True)
    visceral_fat = Column(Float, nullable=True)
    bmr = Column(Float, nullable=True)
    metabolic_age = Column(Float, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="withings_measurements")
