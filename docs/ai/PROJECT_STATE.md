# Project State

**Purpose:** a concise current-state snapshot — the first file read in
Context Rebuild. Answers only: current version, current git HEAD,
completed Sprint, implemented platform modules, architecture status,
known technical debt, next planned Sprint. Nothing else belongs here.

**Where history went:** detailed sprint-by-sprint narrative (what was
built, why, and how it was verified) now lives in
`docs/ai/history/Sprint-N.md`, one file per major sprint number
(`Sprint-10.md` through `Sprint-13.md` today). This file only indexes
which module shipped in which sprint; the "why" and "how" are there,
not repeated here. `docs/BACKLOG.md` still owns future work,
`docs/TECH_DEBT.md` still owns debt detail, `RELEASE_NOTES.md` still
owns the product-facing shipped-feature log.

**Not hand-maintained.** Claude updates this file at the end of every
sprint as a standing part of Definition of Done — never wait to be
asked. If this file's "Last updated" line is stale relative to
`RELEASE_NOTES.md` or the git log, that itself is a process violation to
flag during the next Context Rebuild.

**Last updated:** 2026-07-09, end of Sprint 13.1 — Release
Announcements, plus this documentation refresh (Sprint 13.1
close-out).

---

## Current Version

`APP_VERSION = "v0.13.0"` (`backend/app/core/version.py`).

## Current Git HEAD

`7e6139b` on `master`, pushed — `origin/master` and local `HEAD` match
exactly.

## Completed Sprint

Sprint 13.1 — Release Announcements (detail:
`docs/ai/history/Sprint-13.md`).

## Implemented Platform Modules

One line per shipped module; full detail in the linked history file.

- Onboarding, Profile, Settings, Find Partner, Organize Match,
  Invitations, Accept/Decline, Match Lifecycle, My Matches, Available
  Matches, Analytics events, Court Registry, Dev/prod environment
  separation — `docs/ai/history/Sprint-10.md`
- Admin Center (auth foundation, Dashboard, Players module), AI
  Context Rebuild workflow, Invite a Friend, Match Discovery Refactor
  Phase 1, Tournament Stabilization Phase 1 — `docs/ai/history/Sprint-11.md`
- Tournament Platform v1 Phase 1, Schema Recovery ops tooling (TECH-010
  mitigation), Coach UX Refactor, Player Platform Refactor (Universal
  Player Picker + Presenter) — `docs/ai/history/Sprint-12.md`
- Release Announcements — `docs/ai/history/Sprint-13.md`

## Architecture Status

- Handlers → Services → Repositories, strictly. Handlers never contain
  business logic and never touch a repository directly.
- Presenter layer established (`bot/presenters/`) for screens whose
  view-assembly is shared across entry points and branchy enough to
  warrant separating from handler orchestration — see
  `docs/ARCHITECTURE.md` §3a for when to use one. Three exist today:
  Tournament Details, Player Card, Release Announcement.
- `OperatorPermission` fully independent of `Player` — no `is_admin` or
  `role` column on `Player`, ever. `PermissionService` authorizes;
  `AdminSessionService` authenticates — never merged.
- Every Admin Center record module = Search → Browse → Details →
  Actions (`docs/ARCHITECTURE.md` §12). Back always returns to that
  module's own Root, never the exact prior screen.
- All user-entered free text (`first_name`, `username`, custom court
  names, tournament name) must be escaped for its `parse_mode` before
  display.
- Rating/reputation/ranking is a permanent product non-goal.
- `TournamentService.can_create_tournament()` (blanket) and
  `can_manage_tournament()` (ownership-aware) stay two separate
  methods — never merged; a future Tournament Organizer permission
  will answer these two questions differently.
- `game.area`/`game.court` come from Organize Match's own Area/Court
  steps, never implicitly from `player.home_area`/`preferred_courts`.
- Never commit or push without explicit approval.

## Known Technical Debt

Full detail in `docs/TECH_DEBT.md`. Summary, by ID:

| ID | Title | Status |
|---|---|---|
| TECH-001 | Duplicated button trigger strings in handler modules | Open |
| TECH-002 | `create_invitation()` returns `None` for multiple distinct failure reasons | Open |
| TECH-003 | No tracking of users who have blocked the bot | Open |
| TECH-004 | Emoji usage not fully centralised | Open |
| TECH-005 | Callback data strings generated inline at every call site | Open |
| TECH-006 | Race condition in game status transitions on PostgreSQL | Open |
| TECH-007 | Intermittent Cancel Match issue on newly created OPEN doubles matches | Investigate — not reproducible |
| TECH-008 | Optimize lazy expiration for large datasets | Open |
| TECH-009 | Duplicate lifecycle advancement after player joins | Accepted technical debt |
| TECH-010 | `create_all_tables()` startup safety net causes schema drift with Alembic | Deferred — symptom repair tool shipped (`scripts/schema_recovery.py`), root mechanism itself not yet fixed |

## Next Planned Sprint

Sprint 13.2 — Tournament Engine (Phase 1). Scope recorded in
`docs/ai/ACTIVE_SPRINT.md`.
