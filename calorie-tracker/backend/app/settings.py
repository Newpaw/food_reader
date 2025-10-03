# All comments are in English as requested.
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./calories.db"
    JWT_SECRET: str = "CHANGE_ME"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "backend/uploads"
    OPENAI_API_KEY: str = "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"
    LLM_MODEL: str = "gpt-4o"

settings = Settings()