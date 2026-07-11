import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from . import logger as logger_module
from . import models, schemas
from .database import init_db
from .logger import RequestLoggingMiddleware, get_logger
from .security import SecurityMiddleware
from .settings import settings

# The timing decorator preserves endpoint annotations on a wrapper defined in
# logger.py. Register the application-specific annotation names in that module
# before importing routers so FastAPI can resolve multipart and dependency types.
logger_module.UploadFile = UploadFile
logger_module.AwareDatetime = AwareDatetime
logger_module.Session = Session
logger_module.models = models
logger_module.schemas = schemas

from .routers import auth_router, coach_router, meals_router, media_router, profile_router, users_router, withings_router


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_runtime_security()
    os.makedirs(settings.upload_dir_path, exist_ok=True)
    init_db()
    logger.info("Application started")
    yield


app = FastAPI(title="Food Reader", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    SecurityMiddleware,
    max_body_bytes=settings.MAX_REQUEST_BODY_BYTES,
    auth_limit=settings.AUTH_RATE_LIMIT_REQUESTS,
    auth_window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    analysis_limit=settings.ANALYSIS_RATE_LIMIT_REQUESTS,
    analysis_window_seconds=settings.ANALYSIS_RATE_LIMIT_WINDOW_SECONDS,
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(meals_router.router)
app.include_router(profile_router.router)
app.include_router(withings_router.router)
app.include_router(coach_router.router)
app.include_router(media_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
