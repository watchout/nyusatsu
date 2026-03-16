"""Application settings via Pydantic Settings.

.env is loaded automatically from the project root (src/backend/../../.env).
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: src/backend/../../ = repository root
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://nyusatsu:nyusatsu_dev@localhost:5433/nyusatsu"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # --- LLM API ---
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    LLM_MAX_TOKENS: int = 4096
    LLM_PROVIDER: Literal["claude", "mock"] = "mock"

    # --- Application ---
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARN", "ERROR"] = "INFO"
    APP_LOG_DIR: str = "logs/"

    # --- Batch scheduling ---
    BATCH_SCHEDULE_CASE_FETCH: str = "0 6 * * *"
    BATCH_SCHEDULE_OD_IMPORT: str = "0 6 * * *"
    BATCH_SCHEDULE_DETAIL_SCRAPE: str = "0 7 * * *"

    # --- Data storage ---
    DATA_RAW_DIR: str = "data/raw/"

    # --- Cost control ---
    LLM_DAILY_TOKEN_LIMIT: int = 0

    # --- Telegram notifications ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- Slack notifications ---
    SLACK_BOT_TOKEN: str = ""
    SLACK_CHANNEL_ID: str = ""


settings = Settings()
