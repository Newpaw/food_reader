from datetime import datetime, timedelta, timezone

import jwt

from .settings import settings


TOKEN_AUDIENCE = "food-reader-media"


def create_media_token(*, meal_id: int, user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "meal_id": meal_id,
        "aud": TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(seconds=settings.MEDIA_URL_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_media_token(token: str) -> tuple[int, int]:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALG],
        audience=TOKEN_AUDIENCE,
    )
    return int(payload["meal_id"]), int(payload["sub"])


def create_media_url(*, meal_id: int, user_id: int) -> str:
    token = create_media_token(meal_id=meal_id, user_id=user_id)
    return f"/uploads/{user_id}/{meal_id}?token={token}"
