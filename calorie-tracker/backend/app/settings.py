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

    # Model routing. LLM_MODEL is the backwards-compatible fallback for every AI workload.
    # Individual workloads can be overridden independently from .env without code changes.
    LLM_MODEL: str = "gpt-5.6-terra"
    MEAL_ANALYSIS_MODEL: str | None = None
    HEALTH_COACH_MODEL: str | None = None
    ASSISTANT_MODEL: str | None = None

    WITHINGS_CLIENT_ID: str | None = None
    WITHINGS_CLIENT_SECRET: str | None = None
    WITHINGS_REDIRECT_URI: str | None = None
    OURA_CLIENT_ID: str | None = None
    OURA_CLIENT_SECRET: str | None = None
    OURA_REDIRECT_URI: str | None = None
    APP_FRONTEND_URL: str = "/profile.html"
    OURA_FRONTEND_URL: str = "/health.html"

    # Public remote MCP server and its built-in OAuth 2.1 authorization server.
    # Production must override the localhost URL with the externally reachable
    # HTTPS origin (for example https://food.example.com).
    MCP_PUBLIC_BASE_URL: str = "http://localhost:8000"
    MCP_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MCP_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "backend/logs"
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_ACCESS_TO_CONSOLE: bool = False

    @property
    def meal_analysis_model(self) -> str:
        return self.MEAL_ANALYSIS_MODEL or self.LLM_MODEL

    @property
    def health_coach_model(self) -> str:
        return self.HEALTH_COACH_MODEL or self.LLM_MODEL

    @property
    def assistant_model(self) -> str:
        return self.ASSISTANT_MODEL or self.LLM_MODEL

    @property
    def upload_dir_path(self) -> Path:
        return _resolve_project_path(self.UPLOAD_DIR)

    @property
    def log_dir_path(self) -> Path:
        return _resolve_project_path(self.LOG_DIR)

    @property
    def mcp_public_base_url(self) -> str:
        return self.MCP_PUBLIC_BASE_URL.rstrip("/")

    @property
    def mcp_resource_url(self) -> str:
        return f"{self.mcp_public_base_url}/mcp"


settings = Settings()
