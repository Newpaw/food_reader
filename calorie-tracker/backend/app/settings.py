from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        if str(path).startswith("/app/"):
            return (PROJECT_ROOT / Path(*path.parts[2:])).resolve()
        return path
    return (PROJECT_ROOT / path).resolve()


def _default_database_url() -> str:
    return f"sqlite:///{(PROJECT_ROOT / 'data' / 'calories.db').resolve()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = _default_database_url()
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 7 * 24 * 60
    UPLOAD_DIR: str = "backend/uploads"
    OPENAI_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    WITHINGS_CLIENT_ID: str | None = None
    WITHINGS_CLIENT_SECRET: str | None = None
    WITHINGS_REDIRECT_URI: str | None = None
    APP_FRONTEND_URL: str = "/profile.html"

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "backend/logs"
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_ACCESS_TO_CONSOLE: bool = False

    @property
    def upload_dir_path(self) -> Path:
        return _resolve_project_path(self.UPLOAD_DIR)

    @property
    def log_dir_path(self) -> Path:
        return _resolve_project_path(self.LOG_DIR)


settings = Settings()
