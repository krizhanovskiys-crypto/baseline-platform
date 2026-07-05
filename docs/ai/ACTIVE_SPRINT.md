# Active Sprint

**Purpose:** the current sprint's checklist only — nothing else. When a
sprint ends, its content moves into `docs/ai/AI_HANDOFF.md` as a dated
entry, `RELEASE_NOTES.md` gets the shipped-feature summary, and this
file is reset for the next sprint.

---

## Current Sprint

Sprint 11.1 — Tournament Stabilization Phase 1, a bug-fixing pass on
top of the still-uncommitted Sprint 12 — Tournament Platform v1 (Phase
1) below. Sprint 11 (Admin Center, Match Discovery Refactor Phase 1) is
complete, committed, and pushed (`b0daea6`).

## Completed — Sprint 11.1 (Tournament Stabilization Phase 1)

- **Task 1 (Verified Coach couldn't create tournaments)** — found to be
  environmental, not a code bug: TECH-010's schema drift left the dev
  database missing `players.is_verified_coach`. Confirmed via a
  controlled test against a correctly-migrated schema that
  `/dev` routing, `can_create_tournament()`, and `tourn_create_start`
  are all already correct for a genuine Coach-only account. No
  permission architecture changed.
- **Task 2 (Registration Deadline didn't auto-close)** — real bug:
  `admin/tournaments.py`'s own Details screen never called
  `check_and_auto_close()`, only the player-facing one did. Fixed by
  wiring the same lazy check into the Admin/Coach Details screen.
- **Task 3 (Registration Closed notification)** — fixed as a direct
  consequence of Task 2's fix; every other close trigger already
  notified correctly. No notification logic redesigned.
- 4 new regression tests (`tests/test_tournament_stabilization.py`):
  Verified Coach can create / Regular Player cannot (both through the
  real handlers, not just the service check), auto-close+notify via
  Admin Details, manual-close notifies every registrant exactly once.

## Completed — Sprint 12 (Tournament Platform v1, Phase 1)

- **Phase 1 — Tournament Platform v1**: `Tournament`/`TournamentPlayer`
  entities; tournament matches are ordinary `Game` rows
  (`Game.tournament_id`, nullable FK) — no new match or invitation
  system
- Registration lifecycle (DRAFT → REGISTRATION_OPEN →
  REGISTRATION_CLOSED → IN_PROGRESS → COMPLETED/CANCELLED), strictly
  forward, mirroring `MatchLifecycleService`'s own pattern
  (`TournamentLifecycleService`)
- Registration auto-closes on whichever comes first: deadline reached,
  `max_players` reached, or manual Admin action — all three funnel
  through one `close_registration()` + the shared Registration Closed
  Notification helper
- Generate Matches: shuffles registered players, requires an even
  count (odd → user-friendly error, no byes), only allowed once
  REGISTRATION_CLOSED, idempotent (checks for existing tournament
  Games first), auto-transitions the tournament to IN_PROGRESS on
  success
- `Player.is_verified_coach` — the first Player Badge, not a separate
  entity — granted/revoked from the existing Player Details screen
  (its first real Actions-layer action)
- Two deliberately separate centralized permission methods:
  `can_create_tournament()` (blanket — Center access/Create/Browse) and
  `can_manage_tournament(telegram_id, organizer_player_id)`
  (ownership-aware — Admin manages any tournament, Verified Coach only
  ones they organized). A Coach viewing a tournament they don't own
  sees Details with no action buttons
- Every generated match's Game always belongs to the Tournament
  Organizer (`GameService.create_game()` gained `auto_join_creator`)
- Tournament creation/management lives only under `/dev`, never the
  Main Menu: Admin gets the full Admin Center via PIN ("🏆
  Tournaments"); Verified Coach gets a narrower Tournament Center with
  no PIN ("🏆 My Tournaments") and no access to Players/Testing/System
- Player-facing Browse/Details/Register/Withdraw reachable from a new
  Main Menu "🏆 Tournaments" button (browsing/registering only — never
  creation)
- Browse ordering: grouped by status (DRAFT → REGISTRATION_OPEN →
  REGISTRATION_CLOSED → IN_PROGRESS → COMPLETED → CANCELLED), then by
  date within each group — sorting only, no status ever filtered out
- Bugfixes caught during self-review and final release verification:
  tournament names and player first_names are free text and were being
  rendered unescaped in several Markdown screens — fixed with the same
  `markdown_decoration.quote()` rule already established elsewhere;
  removed 2 dead-code methods with zero call sites
  (`cancel_tournament()`, `get_registered_player_ids()`); confirmed
  zero Alembic drift and that every callback is reachable and every
  handler is registered

## In Progress

Nothing currently in progress.

## Blocked

Nothing currently blocked.

## Next

**Sprint 12 — Tournament Platform v1, Phase 2** (Round Robin format,
Score Entry, Standings — per `docs/BACKLOG.md` Epic 2), or returning to
Sprint 11's Match Discovery Refactor Phase 2 (repository consolidation)
/ Players Actions layer (suspend/reinstate) — not yet decided, surface
at the next Context Rebuild.
