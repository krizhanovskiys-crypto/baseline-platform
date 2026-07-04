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

**Last updated:** 2026-07-04, end of Sprint 11 — Match Discovery
Refactor Phase 1 (Organize Match Area step) — pending commit/approval.

---

## Current Sprint

Sprint 11 — Admin Center (`docs/BACKLOG.md` Epic 1) + Match Discovery
Refactor (Phase 1 complete; Phase 2 repository consolidation not started).

## Current Branch

`master`

## Current Production Commit

`9d15ece1955061e6e78b27100f023417659814e9` (pushed to `origin/master`).
Match Discovery Refactor Phase 1's changes are implemented and tested
locally but **not yet committed** — awaiting approval.

## Latest Test Count

396 passed, 0 failed (`pytest`, in-memory SQLite, no mocked DB layer) —
locally, on the uncommitted Phase 1 working tree. 389 passed at the
last committed state (`9d15ece`).

## Current Priority

**Sprint 11 — Match Discovery Refactor, Phase 2** (repository
consolidation — optional, pure refactor, lower priority than Phase 1
was). Still open: whether the Players Actions layer (suspend/reinstate —
`docs/BACKLOG.md` Epic 1 Phase 1) happens before or after this.

## Current Task

None in progress. Match Discovery Refactor Phase 1 (mandatory Area step
in Organize Match; Court step shows one merged, starred Favourite+
Registry list scoped to the chosen Area) is implemented, tested, and
awaiting commit approval.

## Next Task

Sprint 11 — Match Discovery Refactor Phase 2 (optional repository
consolidation), or the Players Actions layer — not yet decided.

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
- Never commit without explicit approval. Never push without explicit
  approval.
