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

## Product Principles

Every feature must solve a real user problem.

Always prefer the shortest user flow.

If a feature can be postponed without reducing MVP value, postpone it.

Use language that feels natural to users, not internal technical terminology.

Every feature should improve one of these goals:

- Find the right tennis partner.
- Make organizing a game easier.
- Encourage players to return.
- Keep the interface simple.

Avoid exposing future concepts before they are implemented (rating, reputation, etc.).

Users **organize matches** and **invite players** — use that language in UI strings.

---

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
│   ├── models/   # SQLAlchemy 2.x ORM (Player, Game, GamePlayer, Invitation)
│   └── repositories/ # Data access layer; services talk only to repos
├── schemas/      # Pydantic v2 input/output schemas
└── core/         # Settings (pydantic-settings) and logging setup
```

All new domains must follow the same four-layer structure:

1. **Model** — ORM definition in `database/models/`
2. **Repository** — data access only in `database/repositories/`
3. **Service** — all business logic in `services/`
4. **Handler** — Telegram callbacks/messages in `bot/handlers/`

Handlers never access repositories directly. Business logic belongs only in services. Repositories only access data. Texts stay in `texts.py`. Keyboard builders stay in `keyboards.py`.

### Session flow

The `DatabaseMiddleware` injects a fresh `AsyncSession` into `data["session"]` for every Telegram update. FastAPI uses `Depends(get_db_session)`. Both use `get_session()` from `backend.app.database.session`, which auto-commits on success and rolls back on exception.

Services are instantiated per-request by handlers/routers: `PlayerService(session)`, `GameService(session)`.

### Data model highlights

- `Player.preferred_courts` is stored as a JSON string in a `Text` column. Always use `_player_to_schema()` from `player_service.py` to convert Player ORM → `PlayerRead` — never call `PlayerRead.model_validate(player)` directly, as it will fail to deserialize `preferred_courts`.
- `Player.level_source` is a `String(32)` column (`"self_rated"`, `"coach_verified"`). Defaults to `"self_rated"` automatically when `skill_level` is first set via `update_profile`.
- `Player.is_profile_complete` property checks that `language`, `skill_level`, `home_area`, and `preferred_courts` are all set — guards entry to all features.
- Partner matching filters by same `home_area` and `skill_level` within ±0.5 NTRP, sorted by shared courts → skill diff → recency.
- `available_now` expires after 2 hours (`available_until` timestamp); no background job yet — expiry is checked at query time in the repository.
- `Invitation` has status `PENDING / ACCEPTED / DECLINED`. Accepting an invitation also adds the player to `GamePlayer`.

### Bot FSM

Multi-step wizards use `aiogram.fsm.state.StatesGroup`. All state classes live in `backend/app/bot/states/states.py`:
- `OnboardingStates` — 4 steps: language → level → area → courts
- `FindPartnerStates` — browsing (one-at-a-time pagination)
- `OrganizeMatchStates` — 7 steps including confirm
- `FindPlayersForMatchStates` — browsing candidates after match creation
- `SettingsStates` — main + 4 change sub-states

FSM state is stored in `MemoryStorage` and is lost on bot restart.

### Localization

`backend/app/bot/texts.py` exports `t(key, lang, **kwargs)` for all bot strings. `AREAS`, `SKILL_LEVELS`, and `COURTS` constants are also defined there (Toronto-area defaults).

### Config

`get_settings()` returns a cached `Settings` singleton loaded from `.env`. Key vars: `BOT_TOKEN`, `DATABASE_URL` (defaults to `sqlite+aiosqlite:///./baseline.db`), `APP_ENV`, `DEBUG`, `DEVELOPER_IDS` (comma-separated Telegram IDs for `/dev` access).

`list[int]` fields must not be used directly in `Settings` — pydantic-settings tries to JSON-decode them from env. Use `str` with a `@property` parser instead (see `developer_ids` / `developer_ids_list`).

---

## Database

All schema changes must use Alembic migrations (`alembic revision --autogenerate`). Apply with `alembic upgrade head`.

Never rely solely on `create_all_tables()` for schema changes in a live database — it creates missing tables but never alters existing ones. Use it only as a safety net on first startup.

Register every new model in `backend/app/database/models/__init__.py` so Alembic detects it during autogenerate.

Tests hit a real in-memory SQLite database — no mocking of the DB layer. Each test gets a fresh `engine` and `session` fixture from `tests/conftest.py`. `pytest-asyncio` is configured with `asyncio_mode = auto`.

---

## UX

Prefer simple, conversational wording.

### Emoji System

One meaning per emoji — never reuse an emoji across different semantic roles.

| Emoji | Meaning | Use |
|-------|---------|-----|
| 🎾 | Tennis data | Skill level labels, match type (Singles/Doubles), NTRP values, preferred courts |
| ⭐ | Skill level value | Profile field — NTRP level display |
| 📖 | Level source | Profile field — self-rated or coach-verified label |
| 🏠 | Home / menu | Main menu header and all "back to menu" buttons |
| 🔍 | Search | Finding partners, finding players for a match |
| 👥 | Group / players | Player counts, roster, "we found N players" |
| 📨 | Invitation | Invitation received header |
| 🎉 | Milestone | Match full, match confirmed — celebratory events |
| 😔 | Empty state | No results found (partners, players) |
| 📋 | List | My matches, invited players list, game count in stats |
| ➡️ | Forward | Next button (always with variation selector) |
| ⬅️ | Back | Previous / back buttons |
| 📅 | Date / activity | All dates; also matches-played count in profile |
| 🕒 | Time | All times |
| 📍 | Location | Courts, areas |
| ✅ | Success / done | Confirmations, "Done" button, positive outcomes |
| ❌ | Cancel / decline | Cancel actions, decline buttons, error messages |
| ⚠️ | Warning | Incomplete profile, generic errors |
| 🔥 | Urgency | Available Now feature |
| 👤 | Profile | Single player / personal profile |
| 💬 | Contact | Contact a player |
| ✉️ | Sent | Invite sent confirmation |
| 📨 | Invite action | Send invitation button (also invitation received header) |
| 🌍 | Language | Language selection |
| ⚙️ | Settings | Settings menu |
| 🏟 | Court venue | Court selection |
| ✏️ | Edit | Edit profile, change level |
| 🏆 | Verified | Coach-verified level badge |
| 📊 | Statistics | Developer stats header only |

Never add catch-all or generic fallback handlers. Unknown messages must remain unhandled during development — silence exposes routing bugs; a catch-all hides them. If a message is not reaching the right handler, fix the router registration or state filter, not the symptom.

Telegram `ReplyKeyboardMarkup` caching is not a routing bug. The keyboard refreshes when the bot sends a new one (e.g. via `/start` or Main Menu). Refresh it through explicit UX flows, never through a fallback handler.

Do not surface internal field names, numeric IDs, or future concepts (rating, reputation scores) in user-facing messages.

---

## Development Workflow

Before implementing any feature, answer:

1. What user problem does this solve?
2. What is the shortest flow?
3. What can wait until a later sprint?

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

## Testing

Every completed feature must include:

- `pytest` (run once after all changes)
- bot startup verification (`python -m backend.app.bot.main` or dispatcher build check)
- manual Telegram verification when user interaction changes

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
