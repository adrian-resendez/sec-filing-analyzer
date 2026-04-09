from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ai_provider: str = "gemini"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    sec_api_key: str = ""
    sec_user_agent: str = "FilingIntelligence/1.0 (you@example.com)"
    massive_api_key: str = ""
    database_url: str = "postgresql://postgres:postgres@db:5432/sec_analyzer"
    redis_url: str = "redis://redis:6379/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        ai_provider=os.getenv("AI_PROVIDER", "gemini"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        sec_api_key=os.getenv("SEC_API_KEY", ""),
        sec_user_agent=os.getenv(
            "SEC_USER_AGENT", "FilingIntelligence/1.0 (you@example.com)"
        ),
        massive_api_key=os.getenv("MASSIVE_API_KEY", ""),  # ✅ FIXED
        database_url=os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@db:5432/sec_analyzer"
        ),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    )