import os
from pathlib import Path

from sqlalchemy import create_engine
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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
