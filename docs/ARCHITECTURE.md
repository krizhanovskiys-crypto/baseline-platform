# Baseline Architecture

**Purpose:** explains **how** the system is organized — the technical
reference for adding or changing anything in the codebase.

**What belongs here:** the layer diagram, folder responsibilities,
business-logic placement rules, repository/FSM/registry/lifecycle
architecture, project conventions, and the checklist for adding a new
feature.

**What must never be duplicated here:** *why* a feature is built the way
it is, or product framing (→ `docs/PRODUCT_DECISIONS.md`), mandatory
MUST/MUST NOT engineering rules (→ `docs/engineering/CONSTITUTION.md`),
or a folder-tree summary for newcomers (→ `README.md`, which points here
for detail instead of keeping its own copy).

This is a living document — update it when the architecture changes, not
just when someone remembers to.

---

## 1. Overall architecture

```
Telegram Bot (aiogram)
        ↓
    Handlers          — coordinate flow, call one service, render a reply
        ↓
    Services          — all business logic, transport-agnostic
        ↓
    Repositories       — data access only, no rules
        ↓
    Database (SQLAlchemy async ORM, SQLite/Postgres)
```

A REST API (`backend/app/api/`) exists alongside the bot and calls into the
**same service layer** — services never assume they're being called from
Telegram. Anything that works from the bot must work identically from the
API, because there is exactly one place business rules live.

Every layer only talks to the layer directly below it. A handler never
touches a repository or the ORM directly; a service never touches aiogram
types; a repository never contains an `if` that encodes a business rule.

---

## 2. Folder responsibilities

```
backend/app/
├── bot/
│   ├── handlers/     one file per feature (find_partner.py, organize_match.py, ...)
│   ├── keyboards/     keyboards.py — pure functions, no state, no side effects
│   ├── states/        states.py — every FSM StatesGroup, one place
│   ├── texts.py        all UI strings, keyed by language; t(key, lang, **kwargs)
│   ├── middlewares/    database.py — injects a fresh session per update
│   └── main.py          builds the dispatcher, registers every router
├── api/v1/               FastAPI routers — thin, call services, no logic
├── services/              business logic, transport-agnostic
├── database/
│   ├── models/            SQLAlchemy ORM
│   └── repositories/      data access, one repository per aggregate
├── schemas/                Pydantic v2 request/response shapes
├── data/                    static reference registries (e.g. Court Registry)
├── insights/                 analytics: repository.py + service.py, same pattern as any other domain
└── core/                      Settings (pydantic-settings) and logging setup
```

`backend/app/data/` is for registries that are real data but don't yet
warrant a database table — currently just the Court Registry
(`courts.py`). If a registry starts needing writes, per-user overrides, or
relational queries, that's the signal to promote it to a proper
Model → Repository → Service, not to keep bolting behavior onto the data
module.

---

## 3. Business logic rules

**Business logic belongs in Services, not in Handlers.** This is the one
rule everything else in this document supports.

A handler's job is narrow: parse the incoming update, call exactly one
service method, render the result. If a handler contains an `if` that
decides *whether something is allowed* (not just *whether to show screen A
or screen B*), that check almost certainly belongs in a service instead.

Concretely, a service method is responsible for:
- Every read/write that touches more than one repository.
- Every invariant ("a match must be OPEN before it can be joined," "a
  created match must be immediately visible").
- Anything that must behave identically whether called from the bot or
  the REST API.

A handler is responsible for:
- FSM state transitions (which screen comes next).
- Building the reply (calling a keyboard factory, calling `t()`).
- Translating a callback/message into a service call and its arguments.

If you find yourself writing DB queries, status checks, or multi-step
"do X then Y" logic inside a handler, stop — it belongs in
`backend/app/services/`.

---

## 4. Repository responsibilities

Repositories are data access **only** — no business rules, no
cross-repository orchestration. Each repository owns one model (or a
tightly related pair, e.g. `GameRepository` / `GamePlayerRepository`) and
exposes query methods named for what they return
(`get_upcoming_matches_for_player`, not a generic `filter(**kwargs)`).

`BaseRepository` (`database/repositories/base.py`) provides the common
`get_by_id` / `get_all` / `add` / `delete` primitives; specific
repositories add domain queries on top. A repository method may combine
`and_`/`join`/`order_by` however it needs to, but it must not decide
things like "is this transition allowed" — that's a service's job
(see `MatchLifecycleService`, section 6).

Services instantiate the repositories they need in `__init__`, and are
the only thing that talks to more than one repository in a single
operation.

---

## 5. State management (FSM)

Multi-step conversational flows use `aiogram.fsm.state.StatesGroup`. All
state classes live in one file, `backend/app/bot/states/states.py` — never
scattered across handler files. Current groups: `OnboardingStates`,
`OrganizeMatchStates`, `FindPartnerStates`, `FindPlayersForMatchStates`,
`AvailableMatchesStates`, `ConfirmMatchStates`, `SettingsStates`.

Conventions:
- FSM state is stored in `MemoryStorage` and is **lost on bot restart** —
  don't rely on it surviving a deploy mid-flow.
- A free-text input step (e.g. "enter the court name") gets its own state
  (`enter_custom_*`) rather than trying to detect free text inside a
  callback-only state.
- Two different features may reuse the same `callback_data` prefix (e.g.
  `court_toggle:`) as long as they're gated by different states — aiogram
  routes on state + filter together, so there's no runtime collision. This
  is preferred over writing a near-duplicate handler when an existing
  selector is reused with a different save target (Court Registry's
  `courts_keyboard()` is reused, unchanged, by onboarding, Edit Profile,
  and Find Partner's Smart Filter — three states, one keyboard function).
- A handler that edits a message in place as part of a multi-screen flow
  must tolerate Telegram's "message is not modified" error (re-selecting
  the active option re-renders identical content) — see `_edit_screen()`.

---

## 6. Court Registry architecture

`backend/app/data/courts.py` is the single source of truth for Tennis
Zones and courts:

```python
COURTS_BY_ZONE: dict[str, list[str]]   # the actual data
TENNIS_ZONES: list[str]                # derived from COURTS_BY_ZONE.keys()
get_courts_for_zone(zone) -> list[str] # the only read API callers use
```

It's a pure data + lookup module — no ORM, no session, no side effects.
Callers (`keyboards.py`, bot handlers) depend only on
`get_courts_for_zone()`'s signature, never on the dict's shape, which
makes it a drop-in replacement target for a future database-backed
`Court` model: swap the module's internals for repository calls, and no
caller changes.

Custom courts (a player's own, not in the registry) are **not** a
separate concept at the storage layer — they're stored in the existing
`Player.preferred_courts` field alongside registry courts, as plain
strings. `courts_keyboard(lang, zone, selected)` is what distinguishes
them at render time: registry courts for `zone` render first, then any
`selected` court NOT in that zone's registry renders as an extra checked
button under a "Custom Courts" divider. Both kinds toggle through the
same `court_toggle:{court}` callback — there is no separate code path,
model, or FSM state for "custom" vs. "registry."

Partner matching (`PlayerService.find_partners`) has **zero** awareness
of the registry — it does plain string set-intersection on
`preferred_courts`. This is why adding the registry carried no risk of
matching regressions: the registry is a UI/selection-time concern only.

---

## 7. Match lifecycle architecture

`MatchLifecycleService` (`services/match_lifecycle_service.py`) is the
**sole authority** over `Game.status`. No handler and no other service
may write `Game.status` directly — every transition goes through
`MatchLifecycleService.transition(game_id, new_status)`, which checks a
`_VALID_TRANSITIONS` table and raises `InvalidTransitionError` for
anything not explicitly allowed.

```
DRAFT → OPEN → PARTIALLY_FILLED → FULL → CONFIRMED → IN_PROGRESS → COMPLETED
                    ↘________________↗ (reversible while filling)
              any pre-start status → CANCELLED / EXPIRED
```

Two rules that follow from "sole authority":
- **A match must leave `GameService.create_game()` already usable.**
  `create_game()` transitions `DRAFT → OPEN` itself before returning —
  visibility (My Matches, joinability) is a guarantee the service makes,
  not a step every future caller has to remember. (This was a real bug:
  the bot's Organize Match wizard used to perform this transition itself
  after calling `create_game()`; the REST API path didn't, so matches
  created through it were permanently invisible. Fixed by moving the
  transition into the service.)
- **Expiry is lazy, not scheduled.** There's no background job. Any
  service method that reads match state calls
  `MatchLifecycleService.expire_if_stale()` first, which transitions a
  past-dated pre-start match to `EXPIRED` on read.

---

## 8. Current project conventions

- **One screen per concept, reachable identically from every entry
  point.** If a feature can be reached from the main menu, from a
  just-completed action, and from another screen, all three must render
  through the same handler function — not near-duplicate implementations
  that drift apart (`my_matches.py` is the only Match Details screen;
  there is deliberately no second one).
- **`_player_to_schema()` / `_game_to_schema()` are the only way ORM
  objects become API/bot-facing schemas.** Never call
  `PlayerRead.model_validate(player)` directly — `preferred_courts` and
  `spoken_languages` are JSON-encoded `Text` columns that need explicit
  parsing.
- **Every new ORM model is registered in
  `database/models/__init__.py`**, and every schema change goes through
  an Alembic migration — `create_all_tables()` is a first-run safety net
  only, never a substitute for a migration.
- **No forced migrations for vocabulary/UI changes.** Tennis Zones
  replaced the old Area list's *values* without touching the
  `Player.home_area` column or any Python identifier — old data keeps
  working; only the displayed options changed.
- **Localization:** every user-facing string goes through
  `t(key, lang, **kwargs)` in `texts.py`, defined for all three supported
  languages (en/uk/ru). No hardcoded UI strings in handlers or keyboards.

---

## 9. Rules for adding a new feature

1. **Model** (if new data is needed) → register it in
   `database/models/__init__.py` → Alembic migration.
2. **Repository** — data access only, named query methods.
3. **Service** — business logic, transport-agnostic, usable from bot and
   API identically. This is where invariants live.
4. **Handler** — FSM state + one service call + render. Reuse an existing
   keyboard/state/selector before writing a new one.
5. **Tests** — repository/service tests hit the real in-memory SQLite
   fixture (never mock the DB layer); a bug fix needs a regression test
   that reproduces the original defect.
6. Run the full `pytest` suite and verify the bot dispatcher builds
   before calling anything done.
7. If the change introduces a new architectural pattern (not just a new
   feature using existing patterns), update this document in the same
   change — don't let it drift out of date.

---

## 10. Environment separation

**Goal:** development must never be able to touch production's bot token,
database, or data — by construction, not by discipline.

### Configuration flow

`backend/app/core/config.py` resolves configuration in this order:

```
OS environment variables (highest precedence)
        ↓
dotenv file selected by ENV   (.env.dev / .env.production / .env)
        ↓
field defaults in Settings (lowest precedence)
```

Which dotenv file gets loaded is decided once, at import time, by
`_resolve_env_file()`:

| `ENV` (OS var)          | File loaded      |
|--------------------------|-------------------|
| `development` / `dev`    | `.env.dev`         |
| `production` / `prod`    | `.env.production`   |
| unset, unrecognized, or the mapped file doesn't exist | `.env` (unchanged legacy behavior) |

`Settings` is a singleton (`get_settings()`, `@lru_cache`) — resolved once
per process, not hot-reloaded if `ENV` changes mid-run. `.env`,
`.env.dev`, and `.env.production` are all gitignored; `.env.dev.example`
and `.env.production.example` are the tracked templates (`cp
.env.dev.example .env.dev`, then fill in real values).

### What's environment-specific

Everything comes from the same `Settings` object — no code branches on
"am I in dev or prod," it just reads the config that was resolved for
this process:

| Setting | Development | Production |
|----------|--------------|-------------|
| `BOT_TOKEN` | a separate dev bot — **never** the production token | the real bot |
| `DATABASE_URL` | `sqlite+aiosqlite:///./baseline-dev.db` | `sqlite+aiosqlite:///./baseline.db` (or Postgres) |
| `DEBUG` | `true` | `false` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| SQLAlchemy engine logger | `INFO` (`sqlalchemy.engine.Engine` logs every query) | `WARNING` (concise — no per-query noise) |

The SQLAlchemy verbosity toggle already existed in
`backend/app/core/logging.py` (`INFO if settings.debug else WARNING`) —
nothing there needed to change; supplying the right `DEBUG`/`LOG_LEVEL`
values per environment file is what drives requirement 5 end to end.

### Startup flow

No code changes are needed to start in either environment — only the
`ENV` variable:

```bash
ENV=development python -m backend.app.bot.main   # loads .env.dev
ENV=production  python -m backend.app.bot.main   # loads .env.production
python -m backend.app.bot.main                     # unset ENV -> .env (legacy/current default)
```

### Deployment flow

The production deploy (`.github/workflows/deploy.yml`) is **unchanged** —
it SSHes in, `git reset --hard origin/master`, reinstalls dependencies,
and restarts the `baseline` systemd service. It never sets `ENV`, so it
keeps loading the server's existing `.env` exactly as before
(backward-compatible by construction, not by exception). Adopting
`ENV=production` + `.env.production` on the server is an **optional**
future step (e.g. `Environment=ENV=production` in the systemd unit, or
exporting it before the deploy script's restart) — not required for this
sprint, and deliberately not done here so the live deployment isn't
touched without a dedicated, reviewed change.

Local development should export `ENV=development` (e.g. in a shell
profile or a `direnv .envrc`) so `.env.dev` — and only `.env.dev` — is
ever loaded while working on the project locally.

---

## 11. Admin Center module layout

**Rule (Sprint 11):** every Admin Center capability is its own module in
`backend/app/bot/handlers/admin/` — never added to an existing file.
`dev.py` MUST NOT become a single growing file for every admin tool ever
built.

```
backend/app/bot/handlers/admin/
├── __init__.py   registers every module's router on the package router
├── common.py     lang_for(), authorized_role() — shared by every module below
├── auth.py       /dev, /exit_admin, PIN entry — the access flow itself
├── testing.py    Create Test Players, Reset Test Data, Database Statistics
├── system.py     Environment visibility; Manage Operators is a later phase
├── players.py    (future) player management tools
├── matches.py    (future) match moderation tools
├── courts.py     (future) Court Registry admin tools
├── tournaments.py (future) tournament administration
└── coaches.py    (future) coach verification tools
```

- A new admin tool means a new file in this package, registered in
  `__init__.py` — not a new function appended to `auth.py` or
  `testing.py`.
- Every module imports `authorized_role()`/`lang_for()` from `common.py`
  rather than re-implementing the session check — the same discipline
  `PermissionService` already enforces for role checks (see §3 of the
  Admin Center security model in `docs/PRODUCT_DECISIONS.md`), applied to
  module boundaries instead of call sites.
- `auth.py` stays cross-cutting (the access flow every module depends on)
  and never accumulates tool-specific logic itself.
- `testing.py` owns `show_admin_menu()` — the Admin Center root screen —
  since it's the only module today. As real modules ship, their buttons
  join this same root screen; it does not get reinvented per module.
