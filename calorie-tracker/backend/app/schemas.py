from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field


MealType = Literal["breakfast", "lunch", "dinner", "snack"]
GenderType = Literal["male", "female", "other"]
ActivityLevelType = Literal[
    "sedentary",
    "lightly_active",
    "moderately_active",
    "very_active",
    "extremely_active",
]
GoalType = Literal["weight_loss", "maintenance", "muscle_gain"]
DietaryPreferenceType = Literal["none", "vegetarian", "vegan", "keto", "high_protein", "low_carb"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: EmailStr
    name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MealBase(BaseModel):
    calories: int = Field(..., ge=0)
    protein: int | None = Field(None, ge=0)
    fat: int | None = Field(None, ge=0)
    carbs: int | None = Field(None, ge=0)
    fiber: int | None = Field(None, ge=0)
    sugar: int | None = Field(None, ge=0)
    sodium: int | None = Field(None, ge=0)
    meal_type: MealType
    consumed_at: AwareDatetime = Field(..., description="UTC timestamp with timezone info")
    notes: str | None = None


class MealCreate(MealBase):
    pass


class MealUpdate(BaseModel):
    calories: int | None = Field(None, ge=0)
    protein: int | None = Field(None, ge=0)
    fat: int | None = Field(None, ge=0)
    carbs: int | None = Field(None, ge=0)
    fiber: int | None = Field(None, ge=0)
    sugar: int | None = Field(None, ge=0)
    sodium: int | None = Field(None, ge=0)
    meal_type: MealType | None = None
    consumed_at: AwareDatetime | None = Field(None, description="UTC timestamp with timezone info")
    notes: str | None = None


class MealOut(ORMModel):
    id: int
    calories: int
    protein: int | None = None
    fat: int | None = None
    carbs: int | None = None
    fiber: int | None = None
    sugar: int | None = None
    sodium: int | None = None
    meal_type: str
    consumed_at: AwareDatetime = Field(..., description="UTC timestamp with timezone info")
    notes: str | None = None
    image_url: str | None = None


class TextMealCreate(BaseModel):
    food_description: str = Field(..., min_length=1, description="Text description of the food")
    calories: int | None = Field(None, ge=0)
    protein: int | None = Field(None, ge=0)
    fat: int | None = Field(None, ge=0)
    carbs: int | None = Field(None, ge=0)
    fiber: int | None = Field(None, ge=0)
    sugar: int | None = Field(None, ge=0)
    sodium: int | None = Field(None, ge=0)
    meal_type: MealType | None = None
    consumed_at: AwareDatetime | None = Field(None, description="UTC timestamp with timezone info")
    notes: str | None = None


class MealReanalysis(BaseModel):
    refinement_context: str | None = Field(
        None,
        min_length=1,
        max_length=2000,
        description="Optional clarification supplied after the initial analysis",
    )
    corrections: dict[str, str] | None = Field(
        None,
        description="Legacy correction map for the previous analysis",
    )


class DailySummary(BaseModel):
    date: date
    total_calories: int
    meals: int


class SummaryOut(BaseModel):
    from_dt: AwareDatetime = Field(..., description="From datetime with timezone info")
    to_dt: AwareDatetime = Field(..., description="To datetime with timezone info")
    days: list[DailySummary]


class UserProfileBase(BaseModel):
    height_cm: float | None = Field(None, ge=50, le=300, description="Height in centimeters")
    weight_kg: float | None = Field(None, ge=20, le=500, description="Weight in kilograms")
    age: int | None = Field(None, ge=10, le=120, description="Age in years")
    gender: GenderType | None = Field(None, description="Gender: male, female, other")
    activity_level: ActivityLevelType | None = Field("sedentary", description="Activity level")
    goal: GoalType | None = Field("maintenance", description="Fitness goal")
    dietary_preference: DietaryPreferenceType | None = Field("none", description="Dietary preference")
    custom_calories: int | None = Field(None, ge=0, le=10000)
    custom_protein_g: int | None = Field(None, ge=0, le=1000)
    custom_carbs_g: int | None = Field(None, ge=0, le=2000)
    custom_fats_g: int | None = Field(None, ge=0, le=500)
    custom_fiber_g: int | None = Field(None, ge=0, le=200)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    activity_level: ActivityLevelType | None = None
    goal: GoalType | None = None
    dietary_preference: DietaryPreferenceType | None = None


class UserProfileOut(ORMModel):
    id: int
    user_id: int
    height_cm: float | None
    weight_kg: float | None
    age: int | None
    gender: str | None
    activity_level: str | None
    goal: str | None
    dietary_preference: str | None
    custom_calories: int | None
    custom_protein_g: int | None
    custom_carbs_g: int | None
    custom_fats_g: int | None
    custom_fiber_g: int | None
    bmr: float | None
    tdee: float | None
    target_calories: int | None
    target_protein_g: int | None
    target_carbs_g: int | None
    target_fats_g: int | None
    target_fiber_g: int | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class NutritionTargets(BaseModel):
    calories: int
    protein_g: int
    carbs_g: int
    fats_g: int
    fiber_g: int
    calculation_method: str = Field(..., description="Method used for calculation")
    bmr: float | None = Field(None, description="Basal Metabolic Rate")
    tdee: float | None = Field(None, description="Total Daily Energy Expenditure")
    last_updated: AwareDatetime = Field(..., description="When profile was last updated")
