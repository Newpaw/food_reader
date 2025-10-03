# All comments are in English as requested.
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./calories.db"
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "backend/uploads"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    LLM_MODEL: str = "gpt-4o"

settings = Settings()