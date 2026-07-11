from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai_analyzer import answer_coach_question
from ..coach_service import (
    DISCLAIMER,
    apply_adaptive_target,
    build_today,
    build_weekly,
    coach_context,
    get_daily_checkin,
    resolve_timezone,
    save_daily_checkin,
)
from ..deps import get_current_user, get_db


router = APIRouter(prefix="/coach", tags=["coach"])


@router.get("/today", response_model=schemas.CoachTodayOut)
def today(
    timezone_name: str | None = Query(None, alias="timezone", max_length=64),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return build_today(db, user.id, timezone_name)


@router.get("/weekly", response_model=schemas.CoachWeeklyOut)
def weekly(
    timezone_name: str | None = Query(None, alias="timezone", max_length=64),
    days: int = Query(7, ge=7, le=28),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return build_weekly(db, user.id, timezone_name, days)


@router.get("/checkin", response_model=schemas.DailyCheckinOut | None)
def checkin(
    timezone_name: str | None = Query(None, alias="timezone", max_length=64),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    day = datetime.now(resolve_timezone(timezone_name)).date()
    row = get_daily_checkin(db, user.id, day)
    if row is None:
        return None
    return schemas.DailyCheckinOut(
        date=day,
        hunger=row.hunger,
        energy=row.energy,
        sleep_hours=row.sleep_hours,
        steps=row.steps,
        trained=bool(row.trained),
        note=row.note,
    )


@router.put("/checkin", response_model=schemas.DailyCheckinOut)
def update_checkin(
    payload: schemas.DailyCheckinIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return save_daily_checkin(db, user.id, payload)


@router.post("/adaptive-target/apply", response_model=schemas.UserProfileOut)
def apply_target(
    timezone_name: str | None = Query(None, alias="timezone", max_length=64),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        return apply_adaptive_target(db, user.id, timezone_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/chat", response_model=schemas.CoachChatOut)
def chat(
    payload: schemas.CoachChatIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    context = coach_context(db, user.id, payload.timezone)
    result = answer_coach_question(payload.question, context)
    return schemas.CoachChatOut(
        answer=result["answer"],
        actions=result.get("actions", []),
        grounded_in=result.get("grounded_in", []),
        disclaimer=DISCLAIMER,
    )
