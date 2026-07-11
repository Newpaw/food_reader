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
WeightSourceType = Literal["manual", "withings"]
CoachPriority = Literal["low", "medium", "high"]


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
    notes: str | None = Field(None, max_length=4000)


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
    notes: str | None = Field(None, max_length=4000)
    correction_reason: str | None = Field(None, max_length=500)


class MealComponent(BaseModel):
    name: str
    estimated_grams: int | None = None
    calories: int
    protein: int = 0
    fat: int = 0
    carbs: int = 0


class MealOut(ORMModel):
    id: int
    food_description: str | None = None
    calories: int
    calorie_min: int | None = None
    calorie_max: int | None = None
    confidence: int | None = None
    protein: int | None = None
    fat: int | None = None
    carbs: int | None = None
    fiber: int | None = None
    sugar: int | None = None
    sodium: int | None = None
    meal_type: str
    consumed_at: AwareDatetime = Field(..., description="UTC timestamp with timezone info")
    notes: str | None = None
    components: list[MealComponent] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    image_url: str | None = None


class TextMealCreate(BaseModel):
    food_description: str = Field(..., min_length=1, max_length=2000, description="Text description of the food")
    calories: int | None = Field(None, ge=0)
    protein: int | None = Field(None, ge=0)
    fat: int | None = Field(None, ge=0)
    carbs: int | None = Field(None, ge=0)
    fiber: int | None = Field(None, ge=0)
    sugar: int | None = Field(None, ge=0)
    sodium: int | None = Field(None, ge=0)
    meal_type: MealType | None = None
    consumed_at: AwareDatetime | None = Field(None, description="UTC timestamp with timezone info")
    notes: str | None = Field(None, max_length=4000)


class MealReanalysis(BaseModel):
    refinement_context: str | None = Field(
        None,
        min_length=1,
        max_length=2000,
        description="Optional clarification supplied after the initial analysis",
    )
    corrections: dict[str, str] | None = Field(None, description="Legacy correction map for the previous analysis")


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
    goal: GoalType | None = Field("weight_loss", description="Fitness goal")
    dietary_preference: DietaryPreferenceType | None = Field("none", description="Dietary preference")
    custom_calories: int | None = Field(None, ge=0, le=10000)
    custom_protein_g: int | None = Field(None, ge=0, le=1000)
    custom_carbs_g: int | None = Field(None, ge=0, le=2000)
    custom_fats_g: int | None = Field(None, ge=0, le=500)
    custom_fiber_g: int | None = Field(None, ge=0, le=200)
    target_weight_kg: float | None = Field(None, ge=20, le=500)
    desired_weekly_loss_percent: float | None = Field(0.6, ge=0.2, le=1.0)


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
    target_weight_kg: float | None
    desired_weekly_loss_percent: float | None
    bmr: float | None
    tdee: float | None
    target_calories: int | None
    target_protein_g: int | None
    target_carbs_g: int | None
    target_fats_g: int | None
    target_fiber_g: int | None
    weight_source: str | None
    weight_measured_at: AwareDatetime | None
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


class CoachMetric(BaseModel):
    current: int
    target: int | None = None
    remaining: int | None = None
    percentage: int | None = None


class CoachAction(BaseModel):
    title: str
    body: str
    priority: CoachPriority
    action_type: str
    suggested_foods: list[str] = Field(default_factory=list)


class DailyCheckinIn(BaseModel):
    hunger: int | None = Field(None, ge=1, le=5)
    energy: int | None = Field(None, ge=1, le=5)
    sleep_hours: float | None = Field(None, ge=0, le=24)
    steps: int | None = Field(None, ge=0, le=100000)
    trained: bool = False
    note: str | None = Field(None, max_length=500)
    timezone: str | None = Field(None, max_length=64)


class DailyCheckinOut(ORMModel):
    date: date
    hunger: int | None = None
    energy: int | None = None
    sleep_hours: float | None = None
    steps: int | None = None
    trained: bool
    note: str | None = None


class CoachTodayOut(BaseModel):
    date: date
    goal: str
    calories: CoachMetric
    protein: CoachMetric
    fiber: CoachMetric
    meals_logged: int
    logging_complete: bool
    adherence_score: int
    next_action: CoachAction
    warnings: list[str] = Field(default_factory=list)
    checkin: DailyCheckinOut | None = None
    disclaimer: str


class WeightTrendOut(BaseModel):
    measurements: int
    latest_weight_kg: float | None = None
    change_kg: float | None = None
    weekly_change_kg: float | None = None
    weekly_change_percent: float | None = None
    direction: Literal["down", "stable", "up", "unknown"]


class AdaptiveTargetOut(BaseModel):
    current_target: int | None = None
    recommended_target: int | None = None
    adjustment: int = 0
    reason: str
    eligible: bool


class CoachWeeklyOut(BaseModel):
    from_date: date
    to_date: date
    logged_days: int
    total_days: int
    logging_completeness_percent: int
    average_calories_all_days: int
    average_calories_logged_days: int
    average_protein_g: int
    average_fiber_g: int
    calorie_target: int | None = None
    days_on_target: int
    weight_trend: WeightTrendOut
    adaptive_target: AdaptiveTargetOut
    wins: list[str]
    focus_next_week: list[str]
    average_hunger: float | None = None
    average_energy: float | None = None
    training_days: int = 0
    estimated_weeks_to_goal: int | None = None


class CoachChatIn(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    timezone: str | None = Field(None, max_length=64)


class CoachChatOut(BaseModel):
    answer: str
    actions: list[str] = Field(default_factory=list)
    grounded_in: list[str] = Field(default_factory=list)
    disclaimer: str


class WithingsAuthUrlOut(BaseModel):
    authorization_url: str


class WithingsStatusOut(BaseModel):
    configured: bool
    connected: bool
    last_sync_at: AwareDatetime | None = None
    latest_weight_kg: float | None = None
    latest_measured_at: AwareDatetime | None = None
    scope: str | None = None


class WithingsSyncOut(BaseModel):
    synced_count: int
    latest_weight_kg: float | None = None
    latest_measured_at: AwareDatetime | None = None
    profile_weight_updated: bool
    last_sync_at: AwareDatetime


class WithingsMeasurementOut(ORMModel):
    id: int
    withings_grpid: str
    measured_at: AwareDatetime
    weight_kg: float | None = None
    fat_free_mass_kg: float | None = None
    fat_ratio: float | None = None
    fat_mass_kg: float | None = None
    muscle_mass_kg: float | None = None
    hydration_kg: float | None = None
    bone_mass_kg: float | None = None
    visceral_fat: float | None = None
    bmr: float | None = None
    metabolic_age: float | None = None
    model: str | None = None
