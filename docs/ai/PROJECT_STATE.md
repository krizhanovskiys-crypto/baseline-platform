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

**Last updated:** 2026-07-04, end of Sprint 11 Phase 3.1A (Empty State →
Invite a Friend) — pending commit/approval.

---

## Current Sprint

Sprint 11 — Admin Center (`docs/BACKLOG.md` Epic 1) + Match Discovery
(Empty State → Invite a Friend, Phase 3.1A).

## Current Branch

`master`

## Current Production Commit

`ab6a61a5b92b394b74e3f4d5ebb4374d5f5d0ce6` (pushed to `origin/master`).
Phase 3.1A's changes are implemented and tested locally but **not yet
committed** — awaiting approval.

## Latest Test Count

389 passed, 0 failed (`pytest`, in-memory SQLite, no mocked DB layer) —
locally, on the uncommitted Phase 3.1A working tree. 382 passed at the
last committed state (`ab6a61a`).

## Current Priority

**Sprint 11 — Match Discovery Refactor.** Phase 3.1A (this entry) was
completed specifically as its prerequisite. Still open: whether the
Players Actions layer (suspend/reinstate — `docs/BACKLOG.md` Epic 1
Phase 1) happens before or after the Match Discovery Refactor.

## Current Task

None in progress. Phase 3.1A (Empty State → Invite a Friend) is
implemented, tested, and awaiting commit approval.

## Next Task

Sprint 11 — Match Discovery Refactor.

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
- Never commit without explicit approval. Never push without explicit
  approval.
