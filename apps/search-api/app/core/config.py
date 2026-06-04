from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_version: str = "mvp"
    database_url: str = "postgresql+psycopg://caselens:caselens@localhost:5432/caselens"
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "dragonkue/multilingual-e5-small-ko"
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
