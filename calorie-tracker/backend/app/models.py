import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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


class OAuthClient(Base):
    """Dynamically registered MCP OAuth client.

    Client metadata is stored as JSON. Confidential client secrets are encrypted
    separately so they are never persisted in clear text inside that metadata.
    """

    __tablename__ = "oauth_clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(String, unique=True, index=True, nullable=False)
    metadata_json = Column(Text, nullable=False)
    client_secret_encrypted = Column(Text, nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)


class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    id = Column(Integer, primary_key=True)
    code_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    client_id = Column(String, index=True, nullable=False)
    scopes_json = Column(Text, nullable=False)
    code_challenge = Column(String, nullable=False)
    redirect_uri = Column(Text, nullable=False)
    redirect_uri_provided_explicitly = Column(Boolean, nullable=False, default=True)
    resource = Column(Text, nullable=False)
    expires_at = Column(UTCDateTime(), index=True, nullable=False)
    consumed_at = Column(UTCDateTime(), nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)


class OAuthTokenGrant(Base):
    """One rotatable MCP access/refresh token pair, stored only as hashes."""

    __tablename__ = "oauth_token_grants"

    id = Column(Integer, primary_key=True)
    access_token_hash = Column(String, unique=True, index=True, nullable=False)
    refresh_token_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    client_id = Column(String, index=True, nullable=False)
    scopes_json = Column(Text, nullable=False)
    resource = Column(Text, nullable=False)
    access_expires_at = Column(UTCDateTime(), index=True, nullable=False)
    refresh_expires_at = Column(UTCDateTime(), index=True, nullable=False)
    revoked_at = Column(UTCDateTime(), nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)


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
    adaptive_calories_enabled = Column(Boolean, nullable=False, default=False)
    adaptive_target_calories = Column(Integer, nullable=True)
    adaptive_target_updated_on = Column(Date, nullable=True)
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
