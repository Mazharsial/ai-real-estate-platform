"""Application configuration via pydantic-settings (12-factor / env-driven)."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    APP_NAME: str = "AI Real Estate Platform"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-insecure-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"

    # AI
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Property data
    RENTCAST_API_KEY: str = ""
    DEFAULT_CITY: str = "Dallas"
    DEFAULT_STATE: str = "TX"

    # Security
    RATE_LIMIT_PER_MINUTE: int = 120
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Email / SMTP — free via a Gmail App Password. Blank => emails are skipped gracefully.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = ""             # defaults to SMTP_USER when blank
    MAIL_FROM_NAME: str = "AI Real Estate Platform"
    APP_BASE_URL: str = "http://localhost:5001"   # used for links inside emails (Flask UI)

    @property
    def mail_from_addr(self) -> str:
        return self.MAIL_FROM or self.SMTP_USER

    @property
    def mail_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    # CORS (comma separated)
    CORS_ORIGINS: str = "http://localhost:5001,http://127.0.0.1:5001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
