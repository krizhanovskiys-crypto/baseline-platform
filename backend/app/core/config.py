"""Application configuration loaded from environment variables.

Environment selection (Sprint 10.4): the OS-level `ENV` variable picks
which dotenv file is loaded — `ENV=development` -> `.env.dev`,
`ENV=production` -> `.env.production`. If `ENV` is unset, or the mapped
file doesn't exist, this falls back to the original `.env` — which is
exactly what every environment used before this existed, so an
unconfigured deployment (e.g. the current production server, which never
sets `ENV`) keeps working with zero changes required.
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE_BY_ENV = {
    "development": ".env.dev",
    "dev": ".env.dev",
    "production": ".env.production",
    "prod": ".env.production",
}


def _resolve_env_file() -> str:
    """Pick the dotenv file to load based on the `ENV` OS variable.

    Resolved once, at import time — matches the existing singleton
    (`get_settings()` is `@lru_cache`d), not meant to be hot-swapped
    mid-process.
    """
    env = os.environ.get("ENV", "").strip().lower()
    candidate = _ENV_FILE_BY_ENV.get(env)
    if candidate and Path(candidate).is_file():
        return candidate
    return ".env"


def _default_app_env() -> str:
    """Default for the `app_env` field when the loaded dotenv file (or a
    real OS env var) doesn't explicitly set APP_ENV — falls back to the
    same `ENV` variable used to pick the dotenv file, so `ENV=production`
    alone is enough to be recognised as production even without a
    matching `APP_ENV=production` line."""
    return os.environ.get("ENV", "development").strip().lower() or "development"


class Settings(BaseSettings):
    """All runtime configuration lives here.

    Values are read from the environment (or the dotenv file selected by
    `_resolve_env_file()`). Never hard-code secrets in source code.
    """

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Telegram ────────────────────────────────────────────────────────────
    # Development MUST use its own bot token — never the production token.
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

    # ── Admin Center ─────────────────────────────────────────────────────────
    # Comma-separated Telegram user IDs seeded as Owner on startup — bootstrap
    # only; every grant after the first Owner exists happens in-app.
    owner_ids: str = ""

    @property
    def owner_ids_list(self) -> list[int]:
        if not self.owner_ids.strip():
            return []
        return [int(x.strip()) for x in self.owner_ids.split(",") if x.strip()]

    # Shared MVP PIN gating Admin Center entry. Never hardcoded, never logged.
    admin_pin: str = ""

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = Field(default_factory=_default_app_env)
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
