# Project State

**Purpose:** live project state only — the first file read in Context
Rebuild. Maximum two pages by design; if it's growing past that, move
detail to the file that already owns it (`docs/BACKLOG.md` for future
work, `docs/TECH_DEBT.md` for debt, `RELEASE_NOTES.md` for history) and
keep only a pointer here.

**Not hand-maintained.** Claude updates this file at the end of every
sprint as a standing part of Definition of Done — never wait to be
asked. If this file's "Last updated" line is stale relative to
`RELEASE_NOTES.md` or the git log, that itself is a process violation to
flag during the next Context Rebuild.

**Last updated:** 2026-07-05, end of the Schema Recovery ops-tooling
work — committed.

---

## Current Sprint

No active feature sprint. Most recent committed work: the Schema
Recovery tool (`a11f4c1`), on top of Sprint 11.1 — Tournament
Stabilization Phase 1 bundled with Sprint 12 — Tournament Platform v1,
Phase 1 (`4359146`).

## Current Branch

`master`

## Current Production Commit

`a11f4c1` — schema_recovery.py auto-detection UX refinement, on top of
`350b935` (Schema Recovery tool) and `4359146` (Tournament Platform v1
+ Sprint 11.1 stabilization). **Not yet pushed** to `origin/master`
(last pushed commit is still `b0daea6`).

## Latest Test Count

444 passed, 0 failed (`pytest`, in-memory SQLite, no mocked DB layer) —
locally, on the uncommitted working tree (426 at the last committed
state, `a11f4c1`).

## Current Priority

Sprint 12.2 — Coach UX Refactor is complete and awaiting CTO approval
to commit. After that: Sprint 12 Phase 2 (Round Robin format, Score
Entry, Standings — per `docs/BACKLOG.md` Epic 2).

## Current Task

None in progress. Sprint 12.2 (decoupling Verified Coach from `/dev`,
unifying Tournament Details into one screen) implemented, tested
end-to-end against the two real accounts from the earlier diagnostic
session, and approved for commit pending final review.

## Next Task

Sprint 12 — Tournament Platform v1 Phase 2 (Round Robin, Score Entry,
Standings), or returning to Sprint 11's Match Discovery Refactor Phase 2
/ Players Actions layer — not yet decided.

## Completed Major Features

- Onboarding, Profile, Settings, Find Partner, Organize Match,
  Invitations, Accept/Decline (v0.3.0)
- Match Lifecycle state machine (Sprint 5.1–5.3)
- My Matches, Match Details, Leave/Cancel Match, lazy expiration
  (Sprint 6.1–6.5)
- Available Matches — browse/filter/join open matches (Sprint 7.0)
- Profile UX redesign, Find Partner Smart Filter (Sprint 7.1–7.2)
- Analytics events foundation (Sprint 10.1)
- Court Registry v1.0 — Tennis Zones, custom courts (Sprint 10.3)
- Dev/production environment separation (Sprint 10.4)
- **Admin Center** auth foundation — `OperatorPermission`,
  `PermissionService`, `AdminSessionService` (PIN, session, lockout,
  audit log) (Sprint 11 Phase 2.1)
- **Admin Center Dashboard** — live Environment/Version/Uptime/stats,
  the permanent root screen (Sprint 11 Phase 2.2)
- **Admin Center Players module** — Search/Browse/Details, the
  reference implementation for all future record modules
  (Sprint 11 Phase 3.0)
- **AI Context Rebuild workflow** — `docs/ai/*`, `PROMPT_START.md`,
  Repository Reality Check, CTO Review (Sprint 11)
- **Empty State → Invite a Friend** (Sprint 11 Phase 3.1A) — every
  player-discovery empty state (Find Partner, Find Players for a Match)
  offers a working Telegram share/deep-link "➕ Invite a Friend" button
  instead of a dead end; consolidated three near-duplicate empty-state
  text keys into one shared `player_discovery_no_results`. Deep-link
  payload carries the inviting player's telegram_id
  (`?start=invite_{telegram_id}`) — not parsed or acted on yet, format
  only, ahead of future referral tracking.
- **Match Discovery Refactor Phase 1** (Sprint 11) — Organize Match
  gained a mandatory Area step (`OrganizeMatchStates.choose_area`):
  defaults to the organizer's home area via "✅ Use my area", but
  "✏️ Change area" opens the full Tennis Zone list — the organizer's
  home_area is no longer silently forced onto `game.area`. The Court
  step now shows one merged list scoped to the chosen Area — favourite
  courts within that zone starred and ordered first, followed by the
  rest of that zone's Court Registry, no separate/duplicated list.
  `find_players_for_match()`, `find_partners()`, and every other
  discovery query were untouched — analysis found the query layer was
  already Match Context–correct; only match *creation* needed fixing.
- **Tournament Platform v1, Phase 1** (Sprint 12) — new `Tournament`/
  `TournamentPlayer` entities; tournament matches are ordinary `Game`
  rows (`Game.tournament_id`, nullable FK), not a new match system.
  Registration auto-closes on deadline OR max_players OR manual Admin
  action, whichever comes first, always firing the Registration Closed
  Notification. Generate Matches shuffles registered players, requires
  an even count, is idempotent, and auto-transitions the tournament to
  IN_PROGRESS. Coach is `Player.is_verified_coach` — a boolean badge,
  not a separate entity — granted/revoked from the existing Player
  Details screen. Tournament creation/management lives only under
  `/dev` (never the Main Menu): Admin gets full Admin Center via PIN
  ("🏆 Tournaments"); Verified Coach gets a narrower Tournament Center
  with no PIN ("🏆 My Tournaments") and no access to Players/Testing/
  System. Two deliberately separate, centralized permission methods —
  `can_create_tournament()` (blanket: Center access/Create/Browse) and
  `can_manage_tournament(telegram_id, organizer_player_id)`
  (ownership-aware: Admin manages any tournament, Verified Coach only
  ones they organized). Every generated match's Game.creator_id is the
  Tournament Organizer, never a pair player (GameService.create_game()
  gained `auto_join_creator: bool = True` for this).
- **Tournament Stabilization Phase 1** (Sprint 11.1) — Admin/Coach's own
  Tournament Details screen now runs the same lazy
  `check_and_auto_close()` + Registration Closed Notification the
  player-facing Details screen already did; previously it never did,
  so a tournament whose deadline had passed stayed REGISTRATION_OPEN
  indefinitely unless a *player* happened to open it. Verified Coach
  tournament creation was confirmed architecturally correct against a
  correctly-migrated schema — the reported failure was TECH-010's
  schema drift (a dev database missing `players.is_verified_coach`), not
  a code defect. **Verified** on a clean schema; **pending** validation
  on the real development database specifically after TECH-010 recovery
  is actually carried out there — not to be treated as fully closed
  end-to-end until that happens.

## Critical Constraints

- Handlers never contain business logic and never touch a repository
  directly — Handlers → Services → Repositories, always.
- `OperatorPermission` is fully independent of `Player` — no `is_admin`
  or `role` column on `Player`, ever.
- `PermissionService` authorizes; `AdminSessionService` authenticates —
  never merge these responsibilities into one service.
- Every Admin Center record module = Search → Browse → Details →
  Actions (`docs/ARCHITECTURE.md` §12). Back always returns to that
  module's own Root, never the exact prior screen.
- All user-entered text (`first_name`, `username`, custom court names,
  and future tournament name / coach bio / club name) must be escaped
  for its `parse_mode` before display.
- Rating/reputation/ranking is a permanent product non-goal.
- Player-discovery empty states share one text key
  (`player_discovery_no_results`) and one keyboard builder
  (`player_discovery_empty_keyboard`) — a new discovery flow reuses
  these rather than adding a near-duplicate.
- The invite deep link's payload is `?start=invite_{telegram_id}` —
  identifies the inviter, but is not parsed or acted on anywhere yet
  (no referral tracking). Adding it later means parsing this same
  payload in `/start`; the share mechanism and button never change.
- `game.area`/`game.court` come from Organize Match's own Area/Court
  steps, never implicitly from `player.home_area`/`preferred_courts` —
  the organizer's profile is only ever a *default*, always overridable,
  never the source of truth for a specific match.
- `TournamentService.can_create_tournament()` (blanket) and
  `can_manage_tournament()` (ownership-aware) must stay two separate
  methods — never merged, per explicit CTO instruction, since a future
  Tournament Organizer permission will answer these two questions
  differently.
- Never commit without explicit approval. Never push without explicit
  approval.
