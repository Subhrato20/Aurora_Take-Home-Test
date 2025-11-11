from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration resolved from the environment."""

    message_api_base_url: HttpUrl = Field(
        default="https://november7-730026606190.europe-west1.run.app",
        description="Base URL hosting the member messages API",
    )
    message_page_size: int = Field(
        default=500,
        ge=1,
        le=1000,
        description="Batch size to use when paginating through member messages.",
    )
    min_similarity: float = Field(
        default=0.18,
        ge=0.0,
        le=1.0,
        description="Similarity threshold before we trust a retrieved answer.",
    )

    class Config:
        env_prefix = "AURORA_QA_"
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
