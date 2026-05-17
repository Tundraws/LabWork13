from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the LLM agent."""

    model_config = SettingsConfigDict(extra="ignore", str_strip_whitespace=True)

    nats_url: str = Field(default="nats://localhost:4222", alias="NATS_URL")
    jaeger_endpoint: str | None = Field(default=None, alias="JAEGER_ENDPOINT")
    ollama_url: str | None = Field(default=None, alias="OLLAMA_URL")
    ollama_model: str = Field(default="llama3.1", alias="OLLAMA_MODEL")
    request_timeout_seconds: float = Field(default=6.0, gt=0, alias="LLM_TIMEOUT_SECONDS")
