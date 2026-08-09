from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..assistant_responses_service import chat_with_food_reader
from ..deps import get_current_user, get_db


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


@router.post("/chat", response_model=AssistantChatOut)
def chat(
    payload: AssistantChatIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_with_food_reader(
        db,
        current_user,
        message=payload.message,
        history=[item.model_dump() for item in payload.history],
        timezone_name=payload.timezone,
        locale=payload.locale,
    )
