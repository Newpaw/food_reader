from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

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
    consumed_at: datetime
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
    consumed_at: Optional[datetime] = None
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
    consumed_at: datetime
    notes: Optional[str]
    image_url: str
    class Config: orm_mode = True

class DailySummary(BaseModel):
    date: datetime
    total_calories: int
    meals: int

class SummaryOut(BaseModel):
    from_dt: datetime
    to_dt: datetime
    days: List[DailySummary]