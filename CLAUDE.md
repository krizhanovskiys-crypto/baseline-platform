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
- `Player.level_source` is a `String(32)` column (`"self_rated"`, `"coach_verified"`). Defaults to `"self_rated"` automatically when `skill_level` is first set via `update_profile`.
- `Player.is_profile_complete` property checks that `language`, `skill_level`, `home_area`, and `preferred_courts` are all set — guards entry to all features.
- Partner matching filters by same `home_area` and `skill_level` within ±0.5 NTRP, sorted by shared courts → skill diff → recency.
- `available_now` expires after 2 hours (`available_until` timestamp); no background job yet — expiry is checked at query time in the repository.

### Bot FSM

Multi-step wizards use `aiogram.fsm.state.StatesGroup`. All state classes live in `backend/app/bot/states/states.py`:
- `OnboardingStates` — 4 steps: language → level → area → courts
- `FindPartnerStates` — browsing (one-at-a-time pagination)
- `CreateGameStates` — 7 steps including confirm
- `SettingsStates` — main + 4 change sub-states

### Localization

`backend/app/bot/texts.py` exports `t(key, lang, **kwargs)` for all bot strings. `AREAS`, `SKILL_LEVELS`, and `COURTS` constants are also defined there (Toronto-area defaults).

### Config

`get_settings()` returns a cached `Settings` singleton loaded from `.env`. Key vars: `BOT_TOKEN`, `DATABASE_URL` (defaults to `sqlite+aiosqlite:///./baseline.db`), `APP_ENV`, `DEBUG`, `DEVELOPER_IDS` (comma-separated Telegram IDs for `/dev` access).

`list[int]` fields must not be used directly in `Settings` — pydantic-settings tries to JSON-decode them from env. Use `str` with a `@property` parser instead (see `developer_ids` / `developer_ids_list`).

### Tests

Tests hit a real in-memory SQLite database — no mocking of the DB layer. Each test gets a fresh `engine` and `session` fixture from `tests/conftest.py`. `pytest-asyncio` is configured with `asyncio_mode = auto`.

### Migrations

The bot calls `create_all_tables()` on startup (creates missing tables, never alters existing ones). For column additions, always create an Alembic migration — `alembic revision --autogenerate` compares live DB against models and generates the diff. Apply with `alembic upgrade head`.

---

## Documentation

Update documentation whenever architecture or workflow changes.

Keep `PRODUCT.md` and `CLAUDE.md` consistent with the current project.

Never leave documentation outdated.

---

## Product Mindset

Baseline is not just a Telegram bot.

Every feature should improve one of these goals:

- Find the right tennis partner.
- Make organizing a game easier.
- Encourage players to return.
- Keep the interface simple.

Prefer better UX over adding more features.

---

## Development Workflow

Always follow this order:

1. Understand the task.
2. Read only the necessary files.
3. Implement only the requested task.
4. Keep architecture unchanged.
5. Run all tests once after implementation.
6. Verify the bot starts.
7. Present a summary.
8. Wait for human review.
9. Commit only after approval.

Never commit automatically.

---

## Scope Control

Never implement future tasks.

Never "improve" unrelated code.

Never refactor unless explicitly requested.

One task = one commit.

---

## Architecture Rules

Business logic belongs in Services.

Repositories only access the database.

Handlers contain no business logic.

Texts stay in `texts.py`.

Keyboard builders stay in `keyboards.py`.

---

## Testing

Run `pytest` only once after all changes.

If startup verification is needed, run it once after tests.

Avoid running repeated verification commands.

---

## Git

Never commit before review.

Commit messages must describe exactly what was implemented.

---

## Communication

Keep responses concise.

Do not explain obvious Python or Git concepts.

When finished, always provide:

- modified files
- test results
- architecture impact
- possible risks

Do not ask for confirmation between implementation steps.

Only ask before potentially destructive operations or git commits.
