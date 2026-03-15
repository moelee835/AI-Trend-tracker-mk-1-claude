"""Application configuration via environment variables."""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: Literal["development", "production"] = "development"
    SECRET_KEY: str = "change-me-in-production-at-least-32-chars"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://aitracker:aitracker_secret@localhost:5432/aitracker"
    DATABASE_SYNC_URL: str = "postgresql://aitracker:aitracker_secret@localhost:5432/aitracker"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_MAX_TOKENS: int = 4096

    # News API
    NEWS_API_KEY: str = ""
    GNEWS_API_KEY: str = ""

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "AI Trend Newsletter"
    SMTP_FROM_EMAIL: str = ""
    SENDGRID_API_KEY: str = ""

    # Scheduler (UTC hours)
    DAILY_COLLECT_HOUR: int = 22  # 07:00 KST
    DAILY_COLLECT_MINUTE: int = 0
    DAILY_REPORT_HOUR: int = 23  # 08:00 KST
    DAILY_REPORT_MINUTE: int = 0
    DAILY_SEND_HOUR: int = 0     # 09:00 KST next day
    DAILY_SEND_MINUTE: int = 0

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
