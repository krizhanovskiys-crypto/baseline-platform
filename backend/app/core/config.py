"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration lives here.

    Values are read from the environment (or a .env file at project root).
    Never hard-code secrets in source code.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Telegram ────────────────────────────────────────────────────────────
    bot_token: str = ""

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./baseline.db"

    # ── Developer ────────────────────────────────────────────────────────────
    # Comma-separated Telegram user IDs, e.g. DEVELOPER_IDS=123456789,987654321
    # Stored as a raw string to avoid pydantic-settings JSON-parsing a list field.
    developer_ids: str = ""

    @property
    def developer_ids_list(self) -> list[int]:
        if not self.developer_ids.strip():
            return []
        return [int(x.strip()) for x in self.developer_ids.split(",") if x.strip()]

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def normalise_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
