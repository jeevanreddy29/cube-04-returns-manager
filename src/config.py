"""
Application configuration using Pydantic Settings.
Reads environment variables with support for dynamic GEMINI_MODEL selection.
Supports serverless environments (Vercel / AWS Lambda) via /tmp directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_db_url() -> str:
    # If running on Vercel or AWS Lambda, the root filesystem is read-only.
    # We must store SQLite in /tmp.
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "sqlite:////tmp/returns_manager.db"
    return "sqlite:///./returns_manager.db"


def _default_storage_dir() -> Path:
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp/storage/images")
    return Path("./storage/images")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gemini AI configuration
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key. If empty, mock evaluation mode is used for testing.",
    )
    gemini_model: str = Field(
        default="gemini-1.5-flash",
        description="Dynamic Gemini model name (e.g. gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash).",
    )
    gemini_timeout_seconds: int = Field(default=45, ge=5, le=120)
    gemini_retry_count: int = Field(default=1, ge=0, le=3)

    # Database
    database_url: str = Field(
        default_factory=_default_db_url,
        description="SQLAlchemy database connection string",
    )

    # Server settings
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    app_port: int = Field(default=8000)
    app_host: str = Field(default="0.0.0.0")

    # Image Storage
    image_storage_dir: Path = Field(default_factory=_default_storage_dir)
    max_image_size_bytes: int = Field(default=10 * 1024 * 1024)

    @field_validator("gemini_model", mode="before")
    @classmethod
    def clean_gemini_model(cls, val: str) -> str:
        if not val or not str(val).strip():
            return "gemini-1.5-flash"
        return str(val).strip()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
