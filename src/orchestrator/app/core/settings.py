from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", str_strip_whitespace=True)

    nats_url: str = Field(default="nats://localhost:4222", alias="NATS_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    jaeger_endpoint: str | None = Field(default=None, alias="JAEGER_ENDPOINT")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, ge=1, le=65535, alias="API_PORT")
    task_timeout_seconds: float = Field(default=12.0, gt=0, alias="TASK_TIMEOUT_SECONDS")
    task_retry_attempts: int = Field(default=3, ge=1, le=5, alias="TASK_RETRY_ATTEMPTS")


def get_settings() -> Settings:
    """Return application settings."""

    return Settings()
