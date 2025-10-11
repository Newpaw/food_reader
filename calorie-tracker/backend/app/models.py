from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import pytz

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC))

    meals = relationship("Meal", back_populates="user")

class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    image_path = Column(String, nullable=True)  # Now nullable to support text-only meals
    calories = Column(Integer, nullable=False)
    protein = Column(Integer, nullable=True)  # in grams
    fat = Column(Integer, nullable=True)      # in grams
    carbs = Column(Integer, nullable=True)    # in grams
    fiber = Column(Integer, nullable=True)    # in grams
    sugar = Column(Integer, nullable=True)    # in grams
    sodium = Column(Integer, nullable=True)   # in milligrams
    meal_type = Column(String, nullable=False)  # breakfast|lunch|dinner|snack
    consumed_at = Column(DateTime, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC))
    is_text_only = Column(Integer, default=0, nullable=False)  # 0 = image-based, 1 = text-only

    user = relationship("User", back_populates="meals")