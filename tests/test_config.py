"""Tests for Sprint 10.4 Phase 1 — environment separation (backend/app/core/config.py).

_resolve_env_file() and _default_app_env() are tested directly (pure
functions) rather than through the cached get_settings() singleton, so
each test is isolated and doesn't depend on process-wide caching or on
which .env file happens to exist in the repo root during the test run.
"""
import os

import pytest

from backend.app.core.config import Settings, _default_app_env, _resolve_env_file


# ── _resolve_env_file() ──────────────────────────────────────────────────────

def test_no_env_var_falls_back_to_dotenv(monkeypatch, tmp_path):
    """Backward compatibility: an unset ENV (every deployment before this
    sprint, including the current production server) must resolve to the
    plain .env file, unchanged."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.chdir(tmp_path)
    assert _resolve_env_file() == ".env"


def test_env_development_uses_env_dev_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.dev").write_text("BOT_TOKEN=x\n")
    assert _resolve_env_file() == ".env.dev"


def test_env_production_uses_env_production_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.production").write_text("BOT_TOKEN=x\n")
    assert _resolve_env_file() == ".env.production"


def test_env_development_falls_back_when_env_dev_missing(monkeypatch, tmp_path):
    """ENV=development but no .env.dev file yet must not crash — falls
    back to .env so the app can still start."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.chdir(tmp_path)
    assert _resolve_env_file() == ".env"


def test_env_aliases_dev_and_prod(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.dev").write_text("BOT_TOKEN=x\n")
    (tmp_path / ".env.production").write_text("BOT_TOKEN=x\n")

    monkeypatch.setenv("ENV", "dev")
    assert _resolve_env_file() == ".env.dev"

    monkeypatch.setenv("ENV", "prod")
    assert _resolve_env_file() == ".env.production"


def test_unrecognized_env_value_falls_back_to_dotenv(monkeypatch, tmp_path):
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.chdir(tmp_path)
    assert _resolve_env_file() == ".env"


def test_env_value_is_case_insensitive(monkeypatch, tmp_path):
    monkeypatch.setenv("ENV", "PRODUCTION")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.production").write_text("BOT_TOKEN=x\n")
    assert _resolve_env_file() == ".env.production"


# ── _default_app_env() ───────────────────────────────────────────────────────

def test_default_app_env_falls_back_to_development(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    assert _default_app_env() == "development"


def test_default_app_env_follows_env_variable(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    assert _default_app_env() == "production"


# ── Settings — environment-driven values end to end ─────────────────────────
# Constructed directly (not via the cached get_settings()) so each test
# controls its own environment without leaking into others.

def test_settings_never_defaults_bot_token_to_a_real_value(monkeypatch, tmp_path):
    """No .env file at all must still construct valid Settings with an
    empty bot token — never silently reuse another environment's token."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    s = Settings(_env_file=None)
    assert s.bot_token == ""


def test_settings_development_env_values(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("BOT_TOKEN", "dev-token")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./baseline-dev.db")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    s = Settings(_env_file=None)

    assert s.bot_token == "dev-token"
    assert s.database_url == "sqlite+aiosqlite:///./baseline-dev.db"
    assert s.is_production is False
    assert s.debug is True
    assert s.log_level == "DEBUG"


def test_settings_production_env_values(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BOT_TOKEN", "prod-token")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./baseline.db")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    s = Settings(_env_file=None)

    assert s.bot_token == "prod-token"
    assert s.database_url == "sqlite+aiosqlite:///./baseline.db"
    assert s.is_production is True
    assert s.debug is False
    assert s.log_level == "INFO"


def test_dev_and_prod_settings_never_share_a_bot_token(monkeypatch):
    """The core safety requirement: given two different environments'
    configuration, the resolved bot tokens must differ."""
    monkeypatch.setenv("BOT_TOKEN", "dev-token")
    dev = Settings(_env_file=None)

    monkeypatch.setenv("BOT_TOKEN", "prod-token")
    prod = Settings(_env_file=None)

    assert dev.bot_token != prod.bot_token


def test_app_env_defaults_from_env_variable_when_app_env_not_set(monkeypatch):
    """If only ENV=production is set (no explicit APP_ENV in the file/env),
    Settings must still recognise itself as production."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENV", "production")

    s = Settings(_env_file=None)

    assert s.app_env == "production"
    assert s.is_production is True
