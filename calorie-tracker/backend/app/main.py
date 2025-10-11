from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import Base, engine
from .settings import settings
from .routers import auth_router, meals_router, users_router
from .logger import RequestLoggingMiddleware, get_logger
import os

Base.metadata.create_all(bind=engine)

# Initialize logger
logger = get_logger(__name__)

app = FastAPI(title="Calorie Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Static serving for uploaded images
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(meals_router.router)

logger.info("Application started")