# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate venv first
source .venv/bin/activate

# Run the Telegram bot
python -m backend.app.bot.main

# Run the REST API
uvicorn backend.app.api.app:app --reload

# Run all tests (no .env needed — tests use in-memory SQLite)
pytest

# Run a single test file
pytest tests/test_player_service.py -v

# Database migrations
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Architecture

This is a tennis matchmaking platform. The Telegram bot is the primary client, with a REST API sharing the same service layer. The key constraint: **handlers never contain business logic** — they call a service and return a response.

```
backend/app/
├── bot/          # Aiogram 3.x Telegram bot
│   ├── handlers/ # One file per feature; no logic, only service calls
│   ├── keyboards/# Inline and reply keyboards
│   ├── states/   # FSM StatesGroup definitions for multi-step wizards
│   ├── texts.py  # All UI strings keyed by language (en/uk/ru); use t(key, lang)
│   └── main.py   # Entrypoint — builds dispatcher, registers middleware+routers
├── api/          # FastAPI REST API
│   └── v1/       # Versioned routers (players, games)
├── services/     # Business logic — transport-agnostic, fully testable
├── database/
│   ├── models/   # SQLAlchemy 2.x ORM (Player, Game, GamePlayer)
│   └── repositories/ # Data access layer; services talk only to repos
├── schemas/      # Pydantic v2 input/output schemas
└── core/         # Settings (pydantic-settings) and logging setup
```

### Session flow

The `DatabaseMiddleware` injects a fresh `AsyncSession` into `data["session"]` for every Telegram update. FastAPI uses `Depends(get_db_session)`. Both use `get_session()` from `backend.app.database.session`, which auto-commits on success and rolls back on exception.

Services are instantiated per-request by handlers/routers: `PlayerService(session)`, `GameService(session)`.

### Data model highlights

- `Player.preferred_courts` is stored as a JSON string in a `Text` column. `PlayerService` handles serialization/deserialization.
- `Player.is_profile_complete` property checks that `language`, `skill_level`, `home_area`, and `preferred_courts` are all set — guards entry to all features.
- Partner matching filters by same `home_area` and `skill_level` within ±0.5 NTRP.
- `available_now` expires after 2 hours (`available_until` timestamp); no background job yet — expiry is checked at query time in the repository.

### Bot FSM

Multi-step wizards use `aiogram.fsm.state.StatesGroup`. All state classes live in `backend/app/bot/states/states.py`:
- `OnboardingStates` — 4 steps: language → level → area → courts
- `CreateGameStates` — 7 steps including confirm
- `SettingsStates` — main + 4 change sub-states

### Localization

`backend/app/bot/texts.py` exports `t(key, lang, **kwargs)` for all bot strings. `AREAS`, `SKILL_LEVELS`, and `COURTS` constants are also defined there (Toronto-area defaults).

### Config

`get_settings()` returns a cached `Settings` singleton loaded from `.env`. Key vars: `BOT_TOKEN`, `DATABASE_URL` (defaults to `sqlite+aiosqlite:///./baseline.db`), `APP_ENV`, `DEBUG`.

### Tests

Tests hit a real in-memory SQLite database — no mocking of the DB layer. Each test gets a fresh `engine` and `session` fixture from `tests/conftest.py`. `pytest-asyncio` is configured with `asyncio_mode = auto`.
