# Active Sprint

**Purpose:** the current sprint's checklist only — nothing else. When a
sprint ends, its content moves into `docs/ai/AI_HANDOFF.md` as a dated
entry, `RELEASE_NOTES.md` gets the shipped-feature summary, and this
file is reset for the next sprint.

---

## Current Sprint

Sprint 11 — Admin Center (`docs/BACKLOG.md` Epic 1)

## Completed

- Phase 2.1 — Auth foundation: `OperatorPermission`, `PermissionService`,
  `AdminSessionService` (PIN, 30-minute session, 3-strike/10-minute
  lockout, audit log), hidden `/dev` + `/exit_admin`
- `handlers/admin/` package structure rule (`common.py`, `auth.py`, one
  file per module) — mandatory for all future modules
- Phase 2.2 — Dashboard: live Environment/Version/Uptime + Users/Active
  Matches/Available Now/Courts stats, the permanent Admin Center root
- Phase 3.0 — Players module: Search Player, Browse Players (20/page),
  Player Details — reference implementation for the Search/Browse/
  Details/Actions module shape
- Bugfix: unescaped `first_name`/`username` crashed Player Details
  (`TelegramBadRequest`) — fixed with aiogram's own
  `markdown_decoration.quote()`
- Decision recorded: all user-entered text must be escaped for its
  `parse_mode` before display, project-wide
- UX polish: Player Details shows spoken Languages, not interface
  language (no operational value for an admin)

## In Progress

Nothing currently in progress.

## Blocked

Nothing currently blocked.

## Next

- Players module Actions layer (suspend/reinstate) — `docs/BACKLOG.md`
  Epic 1 Phase 1, **or**
- Matches module (Search/Browse/Details) — the second record-type
  module, built to the same shape as `players.py`

Not yet decided which comes first — surface this choice during the next
Context Rebuild rather than assuming.
