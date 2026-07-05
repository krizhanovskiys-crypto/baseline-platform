# AI Handoff Log

**Purpose:** updated at the end of every sprint, newest entry first.
Each entry is what a new AI session needs to pick up work with zero
chat history — what changed, what was decided, what's blocked, what's
next. Read last in Context Rebuild, after everything else has given the
full standing picture.

---

## Sprint 12.2 — Coach UX Refactor (not yet committed)

**What changed:**
- Removed the Verified Coach's direct `/dev` path entirely
  (`cmd_dev`) — `/dev` is Admin/Owner only now. A Coach reaches
  tournament features from the Main Menu's own role-aware 🏆
  Tournaments button (`tournament_menu_entry`, the single Role
  Resolver — one `can_create_tournament()` check, one keyboard
  builder, `tournament_menu_keyboard`).
- Added My Tournaments (`TournamentService.list_my_tournaments`,
  `TournamentRepository.count_by_organizer`/
  `get_paginated_by_organizer`) — genuinely filtered to the current
  account's own tournaments, unlike Browse.
- **Follow-up refinement (this pass):** two remaining paths
  (`tourn_do_cancel`, `tourn_delete`) still sent a Coach back to the
  old Tournament Center screen — fixed to be role-aware
  (`show_tournament_menu` for a Coach, unchanged `show_tournament_center`
  for an Admin). No path back to the old screen remains for a Coach.
- **Follow-up refinement (this pass): unified Tournament Details.**
  There is no longer a separate Player Details / Admin Details —
  one `show_tournament_details()` (`bot/handlers/helpers.py`), one
  `tournament_details` text key, one `tournament_details_keyboard()`
  that adds management buttons only if `can_manage_tournament()` is
  True and always adds Register/Withdraw based on the viewer's own
  registration status — an organizer who is also a registered
  participant sees both groups on the same screen. Reached via one
  callback prefix (`tourn:open:<id>`), open to any player, not gated
  by `can_create_tournament()` — viewing/registering was never an
  Admin/Coach-only action and must not become one.
- Verified live against the two real accounts from the earlier
  diagnostic session (Owner+Coach 243843943, pure Coach 9000000000)
  and via a real dispatcher run of Create → Cancel and Create →
  Confirm → Details for the pure Coach, not just unit tests.
- **Second refinement pass:** extracted a new `backend/app/bot/
  presenters/` package (documented in `docs/ARCHITECTURE.md` §3a) —
  no such abstraction existed anywhere in Baseline before this;
  `admin/players.py`'s own Details had the same "everything inline"
  shape, confirmed by inspection rather than assumed. Tournament
  Details' (text, keyboard) construction moved out of
  `show_tournament_details()` into a pure
  `build_tournament_details_view()` (takes only already-fetched data,
  no session/Bot/repository) — trivially unit-testable with no
  database, which the new presenter test in
  `tests/test_coach_ux_refactor.py` demonstrates directly.
- **Second refinement pass: Back navigation fixed.** Was hardcoded to
  Browse regardless of context. Now computed by the orchestrating
  handler (a business/domain decision — ownership, role — that a
  presenter must not make itself) and only placed on the button by the
  presenter: the tournament's own organizer → My Tournaments; an Admin
  viewing someone else's tournament → Admin's own Browse; anyone else
  → the general Browse. Verified live against the real pure-Coach
  account (9000000000) opening their own tournament's Details.

**Architecture changes:** Admin's own path (Dashboard → Tournament
Administration) is completely unchanged. New: `backend/app/bot/
presenters/` as a documented, reusable pattern for future screens
whose view-assembly is shared across entry points and branchy enough
to warrant separating from handler orchestration — see
`docs/ARCHITECTURE.md` §3a for when to reach for one (and, just as
importantly, when not to).

**New decisions:** The presenter pattern itself (§3a) — narrower than a
service, never touches the database, only worth it once a screen is
genuinely shared and branchy.

**Current blockers:** None. 444 passed locally, dispatcher builds
clean. Not committed — waiting for CTO approval.

**Next priority:** commit this sprint, then Sprint 12 Phase 2 (Round
Robin, Score Entry, Standings) or Sprint 11's Match Discovery
Refactor Phase 2 / Players Actions layer.

---

## Ops tooling — Schema Recovery (TECH-010 mitigation)

**What changed:**
- New `scripts/schema_recovery.py` — a permanent, standalone,
  additive-only schema drift repair tool for TECH-010's symptom
  (`create_all_tables()` creating new tables in production without
  ever advancing `alembic_version`, and never altering existing
  tables). Source of truth is the Alembic migration chain itself,
  built fresh in a disposable temp database by actually running
  `alembic upgrade head` there — never the ORM models, and never the
  real target database until `--repair` is explicitly invoked.
- Two modes: `--verify` (read-only, prints every difference) and
  `--repair` (mandatory file backup, additive-only fixes only, refuses
  to run if any non-additive `TYPE MISMATCH` is found, re-verifies
  itself afterward, never writes `alembic_version` — that remains a
  separate, official `alembic stamp head` run by a human).
- Contains no Baseline business logic — never imports `backend.app`.
- New `docs/operations/SCHEMA_RECOVERY.md` — the full standing
  procedure (when to use it / when not to, verify → repair → stamp →
  validate → rollback).
- Verified end-to-end against a precise reproduction of the actual
  reported production incident (exact column types via
  `create_all_tables()`, one real data row) before being reported as
  done: `--verify` found exactly the two known gaps and nothing else;
  `--repair` fixed them, the FK came out correct, the data row survived
  untouched, a second `--repair` run was a true no-op, and the backup
  file opened independently with the data intact.
- New `tests/test_schema_recovery.py` (2 tests) — the one remaining
  automated case: `--verify`/`--repair` against an already-healthy
  database both report nothing to do and exit 0, and `--repair` never
  creates a backup file when there's nothing to repair.

**Architecture changes:** None to Baseline itself. This tool is
deliberately outside `backend/app/` and has no relationship to the
application's runtime behavior.

**New decisions:** None beyond what's recorded in this tool's own
design (three rounds of CTO refinement: migration-chain-as-source-of-
truth over ORM models; the `--verify`/`--repair` split; the final name).

**Current blockers:** None. TECH-010 itself remains deferred — this
tool treats its symptom safely and repeatably; it does not fix the
underlying `create_all_tables()`-in-production mechanism.

**Next priority:** Sprint 12 Tournament Platform v1 Phase 2, or
Sprint 11's Match Discovery Refactor Phase 2 / Players Actions layer —
not yet decided.

---

## Sprint 11.1 — Tournament Stabilization, Phase 1

**What changed:**
- **Task 1 (Verified Coach couldn't create tournaments) — root cause was
  environmental, not a code bug.** `docs/TECH_DEBT.md` TECH-010's schema
  drift meant the local dev `baseline.db` was missing `players.
  is_verified_coach` at the time this was reported (`create_all_tables()`
  creates new tables but never alters existing ones). Confirmed via a
  controlled test against a freshly-migrated schema that
  `can_create_tournament()`, `/dev` routing, and `tourn_create_start`
  all already work correctly for a genuine Coach-only account (no
  operator role) — the live dev database's only real account happened
  to also be an Owner, which meant the pure-Coach path had never
  actually been exercised there. No permission architecture changed.
- **Task 2 (Registration Deadline didn't auto-close) — real bug, fixed.**
  `admin/tournaments.py`'s own `_show_details()` never called
  `check_and_auto_close()` at all — only the player-facing Details
  screen did. A tournament whose deadline had passed stayed
  REGISTRATION_OPEN indefinitely from the Admin/Coach's own point of
  view. Fixed by wiring the same lazy check (+ notification on close)
  into the Admin/Coach Details screen, mirroring the player-side
  pattern exactly. Required threading `bot: Bot` through 7 handler
  functions that call `_show_details()` (aiogram's existing DI, no new
  registration needed).
- **Task 3 (Registration Closed notification) — fixed as a side effect
  of Task 2's fix**, since the notification was already correctly wired
  to every OTHER close trigger (manual close, player-facing lazy
  check, register-reaching-max-players) — the only missing path was
  the one Task 2 fixed. No notification logic was touched or redesigned.
- **Follow-up verification pass**: confirmed both Details handlers
  (Admin/Coach and Player) call the exact same
  `TournamentService.check_and_auto_close()` — one shared service
  method, not two independent implementations. Confirmed no handler
  anywhere calls `TournamentLifecycleService`/`update_status` directly
  — the lifecycle authority (`check_and_auto_close()` →
  `close_registration()` → notify → status update) is untouched by
  handlers. Added 2 more regression tests: the player-facing Details
  path still auto-closes+notifies unchanged (parity confirmed, not just
  assumed), and re-opening Details on an already-closed tournament
  neither re-transitions it nor sends a second notification —
  `check_and_auto_close()`'s own `status != REGISTRATION_OPEN` guard is
  the single idempotency authority both handlers rely on.

**Architecture changes:** None. No permission architecture, Player
Discovery, Player Picker, Favorites, Tournament Results, Badges,
Profile, or UX changed — bug fixing only, per scope.

**New decisions:** None.

**Validation status (Task 1):**
- **Verified** on a correctly-migrated schema — the controlled test in
  `tests/test_tournament_stabilization.py` proves the code path is
  correct.
- **Pending** validation on the real development database, specifically
  *after* TECH-010 recovery is actually carried out there — a clean
  test schema is not proof that the live dev environment's own drift
  has been resolved the same way. Do not treat Task 1 as fully closed
  end-to-end until that real-environment check happens.

**Current blockers:**
- None for the code itself. TECH-010 (the underlying schema-drift
  mechanism) remains tracked and deferred — this sprint did not fix
  TECH-010 itself, only confirmed it was the true cause of Task 1's
  *symptom*, per the validation status above. 424 passed locally,
  dispatcher builds clean.

**Next priority:**
- Return to Sprint 12 Tournament Platform v1 Phase 2 (Round Robin,
  Score Entry, Standings) or Sprint 11's Match Discovery Refactor
  Phase 2 / Players Actions layer — not yet decided.

---

## Sprint 12 — Tournament Platform v1, Phase 1

**What changed (amended before commit, per CTO refinements):**
- Game ownership fixed: `GameService.create_game()` gained an optional
  `auto_join_creator: bool = True` (default preserves all existing
  callers unchanged). Every match Generate Matches creates now belongs
  to the Tournament Organizer (`tournament.organizer_player_id`), never
  to either pair player — the organizer isn't auto-added as a
  participant (`auto_join_creator=False`); both pair players are added
  as CONFIRMED explicitly instead
- Two centralized permission methods, deliberately kept separate (not
  merged — they answer different questions and will diverge further
  once a Tournament Organizer permission exists): `can_create_tournament()`
  (blanket — Tournament Center access, Create, Browse) and
  `can_manage_tournament(telegram_id, organizer_player_id)`
  (ownership-aware — every action on one specific tournament: Edit,
  Open/Close Registration, View/Add/Remove Players, Generate Matches,
  Delete). Admin manages any tournament; Verified Coach manages only
  tournaments they organized themselves. A Coach viewing a tournament
  they don't own sees Details with no action buttons (`can_manage=False`
  on `tournament_details_admin_keyboard`)
- Add Player fixed to follow the established Admin Center Search
  three-way branch (`ARCHITECTURE.md` §12: one match / several / none)
  instead of silently taking the first search result — reuses the
  existing `PlayersService.search()`, not a new one-off search flow
- Coach's Tournament Center is now labeled "🏆 My Tournaments"
  (`is_operator=False`), distinct from the Admin-facing "🏆 Tournament
  Center" header, reinforcing the ownership scope in the UI itself
- Browse ordering (both "My Tournaments" and player-facing Browse):
  grouped by status — DRAFT, REGISTRATION_OPEN, REGISTRATION_CLOSED,
  IN_PROGRESS, COMPLETED, CANCELLED — then by `start_date` within each
  group, via `TournamentRepository.get_paginated()`'s `ORDER BY`. No
  status is filtered out of the query — sorting only — so a future
  archive view for COMPLETED tournaments never needs this query
  touched, only how a caller paginates/filters its results. (Caught and
  fixed a real bug while implementing this: a value-keyed `case()` dict
  doesn't route a bound `Enum` member through the column's type
  adapter and silently matches nothing — switched to the same
  condition/value tuple `case()` shape already used by
  `GameRepository.get_available_matches()`.)

**What changed (final release verification, before commit):**
- Removed 2 dead-code methods with zero call sites anywhere:
  `TournamentService.cancel_tournament()` (never wired to any UI action
  — CANCELLED remains a valid lifecycle transition, just not yet
  reachable from any handler) and
  `TournamentPlayerRepository.get_registered_player_ids()` (superseded
  by `get_registered_players()`/`get_registrations_with_players()`)
- Fixed a second Markdown-escaping gap: Add Player's and Remove
  Player's success messages rendered `player.first_name` directly
  without escaping — same bug class as Player Details' and the
  Registration Closed Notification's own fixes. Added a dedicated
  regression test (`tests/test_tournament_admin_escaping.py`)
- Verified: every emitted `callback_data` has a registered handler and
  vice versa (no unreachable callbacks, no missing registrations); the
  Alembic migration produces a zero-diff `autogenerate` against current
  models (confirmed by generating a throwaway revision with empty
  upgrade/downgrade bodies, then discarding it — no real drift)

**What changed (original implementation):**
- New `Tournament`/`TournamentPlayer` entities. Tournament matches are
  NOT a new entity — Generate Matches creates ordinary `Game` rows
  (`Game.tournament_id`, nullable FK) via the existing
  `GameService.create_game()`, no new match or invitation architecture
- `TournamentLifecycleService` — strictly forward status transitions
  (DRAFT → REGISTRATION_OPEN → REGISTRATION_CLOSED → IN_PROGRESS →
  COMPLETED/CANCELLED), mirroring `MatchLifecycleService`'s pattern
  exactly but with no backward transitions, per the approved diagram
- Registration auto-closes on whichever comes first — deadline reached,
  `max_players` reached, or manual Admin action — all funneling through
  one `TournamentService.close_registration()` plus a shared,
  handler-layer `notify_tournament_registration_closed()` helper (kept
  out of the service layer, which stays transport-agnostic)
- Generate Matches: shuffles registered players, requires an even
  count > 0 (odd → user-facing error, no byes — out of scope), only
  allowed once REGISTRATION_CLOSED, idempotent (checks
  `GameRepository.get_games_by_tournament()` first), auto-transitions
  to IN_PROGRESS on success
- `Player.is_verified_coach` — the first Player Badge (Sprint 12
  decision superseding Epic 3's earlier "Coach distinct from Player"
  framing in `docs/BACKLOG.md`) — a boolean column, not a separate
  model/repository/service. Granted/revoked from the existing Player
  Details screen — its first real Actions-layer action
  (`ARCHITECTURE.md` §12 had reserved this slot since Sprint 11)
- Centralized `TournamentService.can_manage_tournaments()` — Admin
  (active PIN session, same bar as every other Admin Center module) or
  Verified Coach today; a future Tournament Organizer permission only
  requires editing this one method's body
- `/dev` gained a third branch in `auth.py::cmd_dev`: non-operators who
  are Verified Coaches land on a Tournament Center with no PIN at all;
  everyone else sees nothing, exactly as before. One shared
  `show_tournament_center()` screen, reached either via Dashboard
  (Admin, PIN already active) or directly via `/dev` (Coach) — not a
  second admin interface
- New player-facing Main Menu button "🏆 Tournaments" — Browse/Details/
  Register/Withdraw only. Tournament *creation* deliberately does not
  appear there; it stays under `/dev` only, per explicit CTO instruction
- Caught and fixed during self-review, before presenting results:
  tournament names are organizer-entered free text and were being
  rendered unescaped in several Markdown screens (confirm screen,
  Details, Edit prompt, Register/Withdraw success, the closed-
  registration notification) — fixed with the same
  `markdown_decoration.quote()` rule already established for
  `first_name`/`username`/custom court names

**Architecture changes:**
- `GameCreate`/`Game` gained a nullable `tournament_id` — the only
  change to existing match-creation code (`GameService.create_game()`
  passes it straight through, one line)
- New `InvalidTournamentTransitionError` (mirrors `InvalidTransitionError`
  exactly, typed for `TournamentStatus` instead of `GameStatus`)
- `PlayerRead`/`_player_to_schema()` gained `is_verified_coach`;
  `player_details_keyboard()` signature changed to take `player_id` and
  `is_verified_coach` (its Actions layer is no longer empty)

**New decisions:**
- Coach is a Player Badge (`is_verified_coach`), not a separate entity —
  supersedes `docs/BACKLOG.md` Epic 3's earlier MVP wording ("distinct
  from Player"), updated in the same pass
- `docs/BACKLOG.md` Epic 2 now documents the tournament-creation
  permission model (Admin + Coach today, Tournament Organizer later) and
  Epic 3 documents the Player Badge decision — recorded there, not in
  `docs/PRODUCT_DECISIONS.md` yet, since that file is reserved for
  *shipped* decisions and this phase isn't committed yet

**Current blockers:**
- None. Awaiting CTO approval to commit (418 passed locally, dispatcher
  builds clean)

**Next priority:**
- Sprint 12 — Tournament Platform v1 Phase 2 (Round Robin, Score Entry,
  Standings), or returning to Sprint 11's Match Discovery Refactor
  Phase 2 / Players Actions layer — not yet decided

---

## Sprint 11 — Match Discovery Refactor, Phase 1 (Organize Match Area step)

**What changed:**
- Architecture analysis (no code changed) traced all 6 player-discovery
  flows Entry→Service→Repository→Filter→Model. Key finding: the
  discovery *queries* (`find_partners`, `find_players_for_match`) were
  already Match/Player Context–correct at query time — the actual
  player-profile leak was one layer upstream, in Organize Match's
  creation wizard silently setting `game.area = player.home_area` with
  no step ever asking, and scoping the Court step to
  `player.preferred_courts` only
- Implemented Phase 1 only, per CTO approval: Organize Match gained a
  mandatory Area step (`OrganizeMatchStates.choose_area`, wizard is now
  7 steps not 6) — "✅ Use my area ({home_area})" as the one-tap default,
  "✏️ Change area" opens the full Tennis Zone list
  (`area_keyboard(callback_prefix="om_area_zone")`). `game.area` now
  always reflects this explicit choice
- Court step now shows one merged list scoped to the chosen Area:
  favourite courts that fall within that zone are starred (⭐) and
  ordered first (in the zone's own registry order), followed by the
  rest of that zone's Court Registry — no separate/duplicated list, per
  the CTO's UX refinement request
- `find_players_for_match()`, `find_partners()`, `PlayerService`,
  `GameService` discovery logic, and `is_profile_complete` were
  explicitly untouched, per the approved scope

**Architecture changes:**
- None to the discovery/service/repository layers — this phase only
  touches match *creation* (`organize_match.py`), confirming the
  analysis's own conclusion that the query layer needed no change

**New decisions:**
- `game.area`/`game.court` must always come from the match's own
  creation-time choice, never implicitly from the organizer's profile
  — profile values are defaults only, always overridable per match
  (recorded in `docs/ai/PROJECT_STATE.md` Critical Constraints)

**Current blockers:**
- None

**Next priority:**
- Sprint 11 — Match Discovery Refactor Phase 2 (optional repository
  consolidation of the two near-duplicate discovery queries — pure
  refactor, no behavior change, lower priority than Phase 1 was; no
  Strategy pattern, per the CTO's explicit call)

---

## Sprint 11 — AI Context Rebuild + Phase 3.1A (Empty State → Invite a Friend)

**What changed:**
- Introduced the mandatory AI Context Rebuild workflow: `docs/ai/PROJECT_STATE.md`,
  `docs/ai/CTO_MEMORY.md`, `docs/ai/ACTIVE_SPRINT.md`, `docs/ai/AI_HANDOFF.md`,
  and `PROMPT_START.md`, all wired into `CLAUDE.md` as a mandatory,
  self-enforced process (Step 0 Repository Reality Check → Step 1 Context
  Rebuild → Step 2 Project Summary → Step 3 CTO Review → Step 4
  Implementation)
- `docs/ai/PROJECT_STATE.md` is no longer hand-maintained — updating it
  is now a standing part of every sprint's Definition of Done
- Phase 3.1A — every player-discovery empty state (Find Partner "All
  Players" and "Smart Filter" modes, Find Players for a Match) now shows
  a working "➕ Invite a Friend" button (Telegram share-sheet URL
  wrapping a bot deep link) instead of a dead-end message, plus a "⬅️
  Back" button to the right destination per screen
- Consolidated three near-duplicate/dead empty-state text keys
  (`no_partners`, `no_partners_friendly`, `fpm_not_found`) into one
  shared `player_discovery_no_results`, and one shared keyboard builder
  (`player_discovery_empty_keyboard`)
- Follow-up refinement: `player_discovery_no_results` copy updated to
  the approved wording ("🎾 Know someone who'd like to play?..."); the
  invite deep link's payload changed from a flat `?start=invite` to
  `?start=invite_{telegram_id}`, identifying the inviter — format only,
  still not parsed anywhere

**Architecture changes:**
- Repository > `docs/ai/PROJECT_STATE.md` > everything else — the
  repository's actual state (git log, test count, migrations) always
  wins over any document describing it
- New shared helper `build_invite_share_url(bot, lang, telegram_id)`
  (`bot/handlers/helpers.py`) — the deep link's payload is
  `invite_{telegram_id}` by design, not parsed or acted on anywhere yet,
  so referral tracking can be added later by parsing this same payload
  in `/start`, never by changing the share mechanism or the button

**New decisions:**
- None recorded in `docs/PRODUCT_DECISIONS.md` this pass — Phase 3.1A
  is UX/architecture-consistency work applying the existing "no
  duplicated empty-state messages" principle, not a new product
  decision in its own right

**Current blockers:**
- None

**Next priority:**
- Sprint 11 — Match Discovery Refactor (Phase 3.1A was its prerequisite)

---

## Sprint 11 — Admin Center (Phases 2.1, 2.2, 3.0)

**What changed:**
- Built the full Admin Center authentication/authorization foundation:
  `OperatorPermission`, `PermissionService`, `AdminSessionService` (PIN,
  30-minute session, 3-strike/10-minute lockout, audit log)
- Built the Admin Center Dashboard — the permanent root screen with
  live Environment/Version/Uptime/stats
- Built the Players module — Search Player, Browse Players, Player
  Details — the first real record-type module
- Fixed a Markdown-escaping crash in Player Details
  (`TelegramBadRequest: can't parse entities` on any `first_name`/
  `username` containing an unpaired special character)
- Removed interface Language from Player Details (no operational
  value); shows spoken Languages instead

**Architecture changes:**
- `handlers/admin/` is now a package, one file per module — mandatory,
  not optional, for every future Admin Center capability
- Every record module follows Search → Browse → Details → Actions
  (`docs/ARCHITECTURE.md` §12)

**New decisions (`docs/PRODUCT_DECISIONS.md`):**
- Admin Center Architecture — Services-only access from admin handlers,
  `OperatorPermission` independence from `Player`, authentication/
  authorization kept as separate services, modular packages mandatory
- Every Admin Center record module has the same shape
- User-entered text must be escaped for its `parse_mode` before display

**Current blockers:**
- None

**Next priority:**
- Players module Actions layer (suspend/reinstate), or the Matches
  module as the second record-type implementation — not yet decided,
  surface this as a question during the next Context Rebuild
