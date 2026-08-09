import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from .settings import PROJECT_ROOT, settings


Base = declarative_base()


def _resolve_database_url(database_url: str) -> str:
    try:
        url = make_url(database_url)
    except Exception:
        return database_url

    if url.get_backend_name() != "sqlite" or not url.database:
        return database_url

    db_path = Path(url.database)
    if db_path.is_absolute():
        if str(db_path).startswith("/app/") and not db_path.parent.exists():
            db_path = PROJECT_ROOT / Path(*db_path.parts[2:])
    else:
        db_path = (PROJECT_ROOT / db_path).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.resolve()}"


DATABASE_URL = _resolve_database_url(settings.DATABASE_URL)


def _maybe_reset_sqlite_db(database_url: str) -> None:
    try:
        url = make_url(database_url)
    except Exception:
        return

    if url.get_backend_name() != "sqlite" or not url.database:
        return

    reset_flag = os.getenv("RESET_DB", "false").lower() == "true"
    if reset_flag and os.path.exists(url.database):
        os.remove(url.database)
        os.makedirs(os.path.dirname(url.database), exist_ok=True)


_maybe_reset_sqlite_db(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def _ensure_profile_schema() -> None:
    inspector = inspect(engine)
    if "user_profiles" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    missing_columns = []
    if "weight_source" not in existing_columns:
        missing_columns.append(("weight_source", "VARCHAR"))
    if "weight_measured_at" not in existing_columns:
        missing_columns.append(("weight_measured_at", "DATETIME"))
    if "adaptive_calories_enabled" not in existing_columns:
        missing_columns.append(("adaptive_calories_enabled", "BOOLEAN NOT NULL DEFAULT 0"))
    if "adaptive_target_calories" not in existing_columns:
        missing_columns.append(("adaptive_target_calories", "INTEGER"))
    if "adaptive_target_updated_on" not in existing_columns:
        missing_columns.append(("adaptive_target_updated_on", "DATE"))

    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name, column_type in missing_columns:
            connection.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {column_name} {column_type}"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_profile_schema()
