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

**Last updated:** 2026-07-04, end of Sprint 11 (Admin Center Phases 2.1/2.2/3.0).

---

## Current Sprint

Sprint 11 — Admin Center (`docs/BACKLOG.md` Epic 1).

## Current Branch

`master`

## Current Production Commit

`4feaceaff9c56f12c582c7a8be1657d1b28a0e2d` (pushed to `origin/master`)

## Latest Test Count

382 passed, 0 failed (`pytest`, in-memory SQLite, no mocked DB layer).

## Current Priority

Admin Center's Players module (Search/Browse/Details) is the reference
implementation for every future record-type module. The current
priority is deciding which comes next: the Players **Actions** layer
(suspend/reinstate — `docs/BACKLOG.md` Epic 1 Phase 1), or the second
record module (Matches), built the same shape as `players.py`
(`docs/ARCHITECTURE.md` §12).

## Current Task

None in progress. The last shipped task (Player Details shows spoken
Languages instead of interface language) was amended into the Players
commit and pushed.

## Next Task

Not yet assigned — awaiting direction between Players Actions
(suspend/reinstate) and the Matches module. See `docs/ai/ACTIVE_SPRINT.md`
→ Next.

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
- Never commit without explicit approval. Never push without explicit
  approval.
