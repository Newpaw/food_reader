import unicodedata
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..assistant_responses_service import chat_with_food_reader
from ..deps import get_current_user, get_db
from ..recipe_recommender import generate_recipe_recommendation


router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AssistantChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AssistantHistoryMessage] = Field(default_factory=list, max_length=24)
    timezone: str = Field(default="Europe/Prague", max_length=100)
    locale: Literal["cs", "en"] = "cs"


class AssistantChatOut(BaseModel):
    available: bool
    message: str
    sources: list[str]
    model: str | None = None


class RecipeRecommendationIn(BaseModel):
    timezone: str = Field(default="Europe/Prague", max_length=100)
    locale: Literal["cs", "en"] = "cs"


def _normalize_query(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _is_oura_meal_question(message: str) -> bool:
    """Detect requests specifically asking for food logged inside the Oura app.

    Oura's current public API exposed to Food Reader does not provide Oura Meals,
    so these requests must not silently fall back to readiness/sleep/activity data.
    """
    text = _normalize_query(message)
    mentions_oura = any(term in text for term in ("oura", "ouraring", "oura ring"))
    meal_terms = (
        "jidlo",
        "jidla",
        "jidle",
        "strava",
        "meal",
        "meals",
        "food",
        "nutrition",
        "snedl",
        "snedla",
    )
    return mentions_oura and any(term in text for term in meal_terms)


def _oura_meals_unavailable(locale: str) -> AssistantChatOut:
    if locale == "cs":
        message = (
            "Jídla z aplikace Oura zatím nevidím. Oura Public API, přes které je FoodReader připojený, "
            "momentálně neposkytuje Oura Meals ani fotky či nutriční záznamy jídel. "
            "Pokud jsi jídlo zadal jen v Oura, FoodReader ho nepřečte; jídla uložená přímo ve FoodReaderu ale vidím."
        )
    else:
        message = (
            "I cannot currently read meals logged in the Oura app. The Oura Public API used by FoodReader does not expose "
            "Oura Meals, meal photos, or nutrition records. If a meal exists only in Oura, FoodReader cannot read it; "
            "meals saved directly in FoodReader are available."
        )
    return AssistantChatOut(available=True, message=message, sources=[], model=None)


@router.post("/chat", response_model=AssistantChatOut)
def chat(
    payload: AssistantChatIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if _is_oura_meal_question(payload.message):
        return _oura_meals_unavailable(payload.locale)

    return chat_with_food_reader(
        db,
        current_user,
        message=payload.message,
        history=[item.model_dump() for item in payload.history],
        timezone_name=payload.timezone,
        locale=payload.locale,
    )


@router.post("/recipe")
def recipe_recommendation(
    payload: RecipeRecommendationIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_recipe_recommendation(
        db,
        current_user,
        timezone_name=payload.timezone,
        locale=payload.locale,
    )
