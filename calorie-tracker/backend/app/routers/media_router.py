from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models
from ..deps import get_db
from ..media_tokens import decode_media_token
from ..settings import settings


router = APIRouter(tags=["media"])


@router.get("/uploads/{user_id}/{meal_id}")
def get_meal_image(
    user_id: int,
    meal_id: int,
    token: str = Query(..., min_length=20),
    db: Session = Depends(get_db),
):
    try:
        token_meal_id, token_user_id = decode_media_token(token)
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=403, detail="Invalid or expired media link.") from exc

    if token_meal_id != meal_id or token_user_id != user_id:
        raise HTTPException(status_code=403, detail="Invalid media link.")

    meal = db.query(models.Meal).filter(
        models.Meal.id == meal_id,
        models.Meal.user_id == token_user_id,
    ).first()
    if not meal or not meal.image_path:
        raise HTTPException(status_code=404, detail="Meal image not found.")

    image_path = Path(meal.image_path).resolve()
    upload_root = settings.upload_dir_path.resolve()
    if not image_path.is_relative_to(upload_root) or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Meal image not found.")

    return FileResponse(
        image_path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": f"private, max-age={settings.MEDIA_URL_TTL_SECONDS}",
            "X-Content-Type-Options": "nosniff",
        },
    )
