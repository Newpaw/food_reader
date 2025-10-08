from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import make_url
from .settings import settings
import os

Base = declarative_base()

def _maybe_reset_sqlite_db(database_url: str) -> None:
    try:
        url = make_url(database_url)
    except Exception:
        return
    if url.get_backend_name() != "sqlite":
        return

    # get absolute path to the SQLite file
    # url.database už je cesta; u sqlite:///relativni.db vrátí relativní, u sqlite:////abs/… absolutní
    db_path = url.database
    if not db_path:
        return

    reset_flag = os.getenv("RESET_DB", "false").lower() == "true"
    if reset_flag and os.path.exists(db_path):
        os.remove(db_path)
        # pro jistotu vytvoř parent dir
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Reset jen když si řekneš přes RESET_DB=true
_maybe_reset_sqlite_db(settings.DATABASE_URL)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# vytvoření tabulek (idempotentní)
Base.metadata.create_all(bind=engine)
