# Sprint History — Sprint 12

**Purpose:** archived detail for Sprint 12, Sprint 12.2, Sprint 12.3,
and the Schema Recovery ops-tooling that shipped between them. Moved
here from `docs/ai/PROJECT_STATE.md`'s "Completed Major Features" list
(Sprint 13.1 documentation refresh) so that file can stay a concise
current-state snapshot instead of a growing narrative. No information
was removed in the move.

---

## Tournament Platform v1, Phase 1 (Sprint 12)

New `Tournament`/`TournamentPlayer` entities; tournament matches are
ordinary `Game` rows (`Game.tournament_id`, nullable FK), not a new
match system. Registration auto-closes on deadline OR max_players OR
manual Admin action, whichever comes first, always firing the
Registration Closed Notification. Generate Matches shuffles registered
players, requires an even count, is idempotent, and auto-transitions
the tournament to IN_PROGRESS. Coach is `Player.is_verified_coach` — a
boolean badge, not a separate entity — granted/revoked from the
existing Player Details screen. Tournament creation/management lived
only under `/dev` at this point (never the Main Menu — this changed in
Sprint 12.2, below): Admin got full Admin Center via PIN
("🏆 Tournaments"); Verified Coach got a narrower Tournament Center
with no PIN ("🏆 My Tournaments") and no access to Players/Testing/
System. Two deliberately separate, centralized permission methods —
`can_create_tournament()` (blanket: Center access/Create/Browse) and
`can_manage_tournament(telegram_id, organizer_player_id)`
(ownership-aware: Admin manages any tournament, Verified Coach only
ones they organized). Every generated match's Game.creator_id is the
Tournament Organizer, never a pair player (`GameService.create_game()`
gained `auto_join_creator: bool = True` for this).

## Ops Tooling — Schema Recovery (TECH-010 mitigation)

New `scripts/schema_recovery.py` — a permanent, standalone,
additive-only schema drift repair tool for TECH-010's symptom
(`create_all_tables()` creating new tables in production without ever
advancing `alembic_version`, and never altering existing tables).
Source of truth is the Alembic migration chain itself, built fresh in
a disposable temp database by actually running `alembic upgrade head`
there — never the ORM models, and never the real target database until
`--repair` is explicitly invoked.

Two modes: `--verify` (read-only, prints every difference) and
`--repair` (mandatory file backup, additive-only fixes only, refuses to
run if any non-additive `TYPE MISMATCH` is found, re-verifies itself
afterward, never writes `alembic_version` — that remains a separate,
official `alembic stamp head` run by a human). Contains no Baseline
business logic — never imports `backend.app`.

New `docs/operations/SCHEMA_RECOVERY.md` — the full standing procedure
(when to use it / when not to, verify → repair → stamp → validate →
rollback). `--db-path` later made optional — auto-detects from
`DATABASE_URL` (real environment first, then `.env`/`.env.dev`/
`.env.production`), so the same command works unchanged on a laptop
and on the server.

Verified end-to-end against a precise reproduction of the actual
reported production incident (exact column types via
`create_all_tables()`, one real data row): `--verify` found exactly the
two known gaps and nothing else; `--repair` fixed them, the FK came out
correct, the data row survived untouched, a second `--repair` run was a
true no-op, and the backup file opened independently with the data
intact. `tests/test_schema_recovery.py` — the one remaining automated
case: `--verify`/`--repair` against an already-healthy database both
report nothing to do and exit 0.

TECH-010 itself remains deferred — this tool treats its symptom safely
and repeatably; it does not fix the underlying `create_all_tables()`-
in-production mechanism.

## Coach UX Refactor (Sprint 12.2)

Verified Coach fully decoupled from `/dev`; reached instead from the
Main Menu's own role-aware 🏆 Tournaments button. `/dev` is Admin/Owner
only from this point forward — `cmd_dev()` no longer has any Coach
branch at all.

Tournament Details unified into one screen (no separate Player/Admin
variant) via the first Presenter (`bot/presenters/tournament_details.py`)
— management buttons appear only when `can_manage_tournament()` is
true; Register/Withdraw appear independently based on the viewer's own
registration status, so an organizer who is also a registered
participant sees both on the same screen. Reached via one callback
prefix (`tourn:open:<id>`), open to any player, never gated by
`can_create_tournament()`.

Back returns to whichever list a tournament actually belongs to for
the viewer (their own My Tournaments if they organized it, an Admin's
own Browse if they're administering someone else's, or the general
Browse otherwise) — a business decision made by the orchestrating
handler, never by the presenter itself.

Two remaining paths that sent a Coach back to the old Tournament
Center screen after cancelling creation or deleting a tournament
(`tourn_do_cancel`, `tourn_delete`) were made role-aware — an Admin
still sees that screen, a Coach never does again.

Recorded in `docs/PRODUCT_DECISIONS.md`: "Coach UX — Tournament
management belongs to the Player experience, not /dev" (supersedes
Sprint 12's original Verified Coach → /dev → Tournament Center shape).

## Player Platform Refactor (Sprint 12.3)

**Universal Player Picker** (`bot/handlers/player_picker.py`,
`data/player_levels.py`) replacing Tournament Add Player's
free-text-only search with a menu: Search (reuses
`PlayersService.search()` and the existing one-match/several/none
branch unchanged) or All Players (groups by configurable NTRP level
bands, SQL `COUNT` per group, SQL-paginated alphabetical listing per
group, always excluding whichever player ids the active context needs
excluded). Selecting a player registers them immediately and returns
to the same level group and page, not the beginning. The
menu/grouping/pagination/exclusion logic stays consumer-agnostic; only
two small functions branch on which consumer is active (today, only
Tournament's Add Player).

**Universal Player Presenter** (`bot/presenters/player_card.py`) — one
place builds every player card: Name, badges, Level, Languages,
Favourite Courts, Matches, always in that order — migrated into every
screen that used to implement its own formatting: My Profile, Find
Partner, Available Now, Find Players for a Match, and Admin Player
Details (which also gained Matches and the Coach badge in its text for
the first time — previously missing entirely). Caught and fixed a real
escaping gap along the way: Favourite Courts can contain free-text
custom names and weren't being escaped in three of the five prior
implementations. Badges are a list of `Badge(attribute, text_key)`
entries, not an if/else chain — a future badge (Club Organizer,
Tournament Champion, Top Player) is one more list entry, once
`PlayerRead` grows the matching field.

Audited the full repository for every player-card and
player-selection implementation before writing any code — found and
consolidated five inconsistent card implementations and confirmed
which list-only screens (Registered Players, Add Player results, Match
Details participants) had nothing to migrate.

Verified across three separate rounds of live runtime checks against
real accounts, not just the test suite: full Admin/Coach/Player
Telegram-equivalent scenario walkthroughs (including a Regular Player
directly invoking the Add Player callback on someone else's tournament
and confirming the permission gate blocks it, not just the button
being hidden), actual rendered output for every card screen, and Coach
badge byte-for-byte consistency across My Profile, Available Now, and
Admin Player Details for the same real account.

Recorded one item in `docs/BACKLOG.md` (Player Details from
Tournament — tapping a registered player to see their full card),
flagged explicitly as surfaced from this sprint's own audit, not the
original Gap Review.
