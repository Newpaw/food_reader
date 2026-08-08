import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .logger import RequestLoggingMiddleware, get_logger
from .routers import auth_router, meals_router, oura_router, profile_router, users_router, withings_router
from .settings import settings


logger = get_logger(__name__)

# Starlette validates the static directory when StaticFiles is constructed,
# before FastAPI's lifespan hook runs. Ensure it exists for clean installs and CI.
os.makedirs(settings.upload_dir_path, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Application started")
    yield


app = FastAPI(title="Calorie Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir_path)), name="uploads")

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(meals_router.router)
app.include_router(profile_router.router)
app.include_router(withings_router.router)
app.include_router(oura_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
