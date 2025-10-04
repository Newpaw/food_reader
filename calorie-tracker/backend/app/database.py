from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import settings
import os

# Check if database file exists and remove it to recreate schema
if "sqlite" in settings.DATABASE_URL and ":" in settings.DATABASE_URL:
    db_path = settings.DATABASE_URL.split(":")[-1]
    if db_path.startswith("///"):
        db_path = db_path[3:]
        if os.path.exists(db_path):
            os.remove(db_path)

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()