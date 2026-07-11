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
    if os.getenv("RESET_DB", "false").lower() == "true" and os.path.exists(url.database):
        os.remove(url.database)
        os.makedirs(os.path.dirname(url.database), exist_ok=True)


_maybe_reset_sqlite_db(DATABASE_URL)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def _add_missing_columns(table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [(name, sql_type) for name, sql_type in columns.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for name, sql_type in missing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {sql_type}"))


def _ensure_legacy_sqlite_schema() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    _add_missing_columns(
        "user_profiles",
        {
            "weight_source": "VARCHAR",
            "weight_measured_at": "DATETIME",
            "target_weight_kg": "FLOAT",
            "desired_weekly_loss_percent": "FLOAT",
        },
    )
    _add_missing_columns(
        "meals",
        {
            "food_description": "VARCHAR",
            "calorie_min": "INTEGER",
            "calorie_max": "INTEGER",
            "confidence": "INTEGER",
            "analysis_json": "TEXT",
            "analysis_model": "VARCHAR",
            "prompt_version": "VARCHAR",
            "confirmed_at": "DATETIME",
        },
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_legacy_sqlite_schema()
