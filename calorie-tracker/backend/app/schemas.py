from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List, Dict
import pytz

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    class Config: orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MealCreate(BaseModel):
    calories: int
    protein: Optional[int] = None
    fat: Optional[int] = None
    carbs: Optional[int] = None
    fiber: Optional[int] = None
    sugar: Optional[int] = None
    sodium: Optional[int] = None
    meal_type: str
    consumed_at: datetime = Field(..., description="Timestamp with timezone info")
    notes: Optional[str] = None

class MealUpdate(BaseModel):
    calories: Optional[int] = None
    protein: Optional[int] = None
    fat: Optional[int] = None
    carbs: Optional[int] = None
    fiber: Optional[int] = None
    sugar: Optional[int] = None
    sodium: Optional[int] = None
    meal_type: Optional[str] = None
    consumed_at: Optional[datetime] = Field(None, description="Timestamp with timezone info")
    notes: Optional[str] = None

class MealOut(BaseModel):
    id: int
    calories: int
    protein: Optional[int] = None
    fat: Optional[int] = None
    carbs: Optional[int] = None
    fiber: Optional[int] = None
    sugar: Optional[int] = None
    sodium: Optional[int] = None
    meal_type: str
    consumed_at: datetime = Field(..., description="Timestamp with timezone info")
    notes: Optional[str]
    image_url: Optional[str] = None
    class Config: orm_mode = True

class TextMealCreate(BaseModel):
    food_description: str = Field(..., description="Text description of the food")
    calories: Optional[int] = None
    protein: Optional[int] = None
    fat: Optional[int] = None
    carbs: Optional[int] = None
    fiber: Optional[int] = None
    sugar: Optional[int] = None
    sodium: Optional[int] = None
    meal_type: Optional[str] = None
    consumed_at: Optional[datetime] = Field(None, description="Timestamp with timezone info")
    notes: Optional[str] = None

class MealReanalysis(BaseModel):
    meal_id: int
    corrections: Dict[str, str] = Field(..., description="Corrections to the previous analysis")

class DailySummary(BaseModel):
    date: datetime = Field(..., description="Date with timezone info")
    total_calories: int
    meals: int

class SummaryOut(BaseModel):
    from_dt: datetime = Field(..., description="From datetime with timezone info")
    to_dt: datetime = Field(..., description="To datetime with timezone info")
    days: List[DailySummary]