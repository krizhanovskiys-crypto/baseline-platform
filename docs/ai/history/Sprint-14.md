# Sprint History — Sprint 14

**Purpose:** archived detail for Sprint 14 — Tournament Engine (Phase
1). Domain Model, Persistence, and Service Layer only; API Layer and
Telegram UI are separate, not-yet-started steps of the same sprint (see
`docs/ai/ACTIVE_SPRINT.md`). Moved here from `docs/ai/PROJECT_STATE.md`
so that file can stay a concise current-state snapshot instead of a
growing narrative. No information was removed in the move.

**Plan reference:** `docs/Sprint14_Tournament_Engine_Plan.md`,
`docs/PD-001-Tournament-Result-Reporting.md`,
`docs/Baseline_Domain_Model.md` §3/§4,
`docs/Baseline_API_v2_Architecture.md` §9. These were written and
committed (`45ff6d6`) partway through the work below, generically —
without reading the actual repository state first. Reconciled against
what was already built (Sprint 12's `Tournament`/`TournamentPlayer`,
`Player.is_verified_coach`, the existing `OperatorPermission` admin
system): the plan's own Step 1 explicitly flagged `is_admin` as "a
judgment call to make against the real code, not decided here" — that
judgment call was made, and confirmed: no `Player.is_admin`, no
`TournamentEntry` (already `TournamentPlayer`), no separate
`GameStatus`-like enum for tournament matches (already `GameStatus`,
reused).

---

## Persistence (Domain Model implementation)

`Game` gains `round: int | None` and `winner_player_id: int | None`
(FK → `players.id`, `ondelete="SET NULL"`) — migration `e417d3f7d1a4`.
No new `Tournament`/`TournamentEntry` models, no `Player.is_admin`, no
new status enum — all three already existed or were deliberately
rejected (see reconciliation above). Repository tests only, real
in-memory SQLite, per convention.

**Operational bug found and fixed after this shipped:** the real dev
database (`baseline.db`) was never migrated to `e417d3f7d1a4` —
`alembic upgrade head` had only been run against disposable temp
databases during verification, never against the actual dev file. My
Matches and Available Matches both broke in real usage
(`sqlite3.OperationalError: no such column: games.round`), reproduced
against the real database, diagnosed to the exact repository call
(`GameRepository.get_expirable_matches()`), fixed by running
`alembic upgrade head` against `baseline.db` for real. Not a code
defect — the migration itself was already correct and tested.

## Service Layer (Match Lifecycle & Result Flow)

`MatchLifecycleService`: `OPEN → IN_PROGRESS` permitted only when
`game.tournament_id is not None` — a narrow, context-aware exception
inside `transition()`, not a blanket addition to `_VALID_TRANSITIONS`.
An ordinary (non-tournament) match still cannot skip the
invitation-driven `PARTIALLY_FILLED → FULL → CONFIRMED` pipeline
(`test_open_skips_to_in_progress` still guards this) — a real regression
was caught and fixed here during the same step, not shipped and found
later.

`TournamentService` gains:
- `generate_matches()` now requires a **power-of-two** player count
  (`is_power_of_two()`, public — byes are out of scope, so an
  even-but-not-power-of-two count like 6 is rejected, not just odd
  counts) and stamps `round=1` on every generated Game.
- `start_match(game_id, organizer_telegram_id)` — `OPEN → IN_PROGRESS`,
  organizer-only (PD-001 / `can_manage_tournament()`).
- `complete_match(game_id, winner_player_id, organizer_telegram_id)` —
  records the Winner (PD-001: Winner only, no score), transitions to
  `COMPLETED`, validates the winner is one of the match's two
  participants, then calls `_advance_round_if_complete()`.
- `_advance_round_if_complete()` — once every Game in a round is
  `COMPLETED`: pairs that round's winners into the next round, or — if
  exactly one winner remains — marks the tournament `COMPLETED`. No
  odd-winner handling needed: `generate_matches()`'s power-of-two
  upfront check guarantees every subsequent round's winner count is
  also a power of two.
- `get_standings(tournament_id)` — always computed from
  `Game.round`/`winner_player_id`/`status`, never stored; no new
  `TournamentPlayerStatus` value, no migration.

No Notifications are sent from `complete_match()` — deliberately no
stub/logged call either (PD-001 describes a Notification step in its
pipeline diagram, but this was a conscious choice, confirmed
explicitly: Telegram integration and Notifications are later, separate
steps of this same sprint; a stub call today would be dead code with
nothing to log yet).

## UX finish — validate at input time, not just at Generate Matches

`Create Tournament`'s `max_players` step now validates power-of-two
immediately (`tourn_enter_max_players`, reusing the same
`is_power_of_two()` — one rule, checked in two places by design,
defense in depth). Before this, entering `6` was silently accepted at
creation and only rejected later, after players had already registered,
at Generate Matches — a real UX gap, fixed as this sprint's own small
closing step rather than deferred. `texts.py` corrected in all three
languages (`tournament_generate_invalid_player_count`,
`tournament_enter_max_players`, `tournament_error_max_players`) — the
old copy said "even number," which stopped being true the moment the
power-of-two rule shipped.

## What Sprint 14 has NOT touched yet

Per `docs/Sprint14_Tournament_Engine_Plan.md`'s own step numbering, this
sprint so far covers its Step 1 (Domain/Persistence) and part of Step 3
(backend service layer) — not Step 2 (API design/endpoints), Step 4
(Telegram integration), or Step 5 (iOS). `start_match()`,
`complete_match()`, and `get_standings()` are reachable only from
Python/tests today — no REST endpoint, no bot handler, no keyboard
button calls them yet.

## Tests

495 total (483 existing + 12 new for the max_players input validation),
plus the Step 1/Step 2 service-layer tests from earlier in this sprint
(start/complete match, permission rejection, next-round generation,
champion determination, standings). All real in-memory SQLite, no
mocks, per convention.

## Commits

`58d4e8a` — `feat(tournament): add tournament game metadata` (Step 1:
model + migration + repository tests).
`8c15af3` — `fix(tournament): validate power-of-two player count
during creation` (Step 2: service layer + UX finish). Both pushed.
