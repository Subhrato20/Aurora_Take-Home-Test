"""Application configuration and constants."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_HTTP_TIMEOUT = 12.0


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    november_api_base: str = Field(
        default="https://november7-730026606190.europe-west1.run.app",
        alias="NOVEMBER_API_BASE",
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    page_size: int = Field(default=100, alias="PAGE_SIZE", ge=1, le=100)
    max_validator_messages: int = Field(
        default=12, alias="MAX_VALIDATOR_MESSAGES", ge=1, le=20
    )
    name_resolver_max_names: int = Field(
        default=50, alias="NAME_RESOLVER_MAX_NAMES", ge=1, le=200
    )
    cache_path: str = Field(
        default="data/messages_cache.json", alias="MESSAGE_CACHE_PATH"
    )
