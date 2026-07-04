# AI Handoff Log

**Purpose:** updated at the end of every sprint, newest entry first.
Each entry is what a new AI session needs to pick up work with zero
chat history — what changed, what was decided, what's blocked, what's
next. Read last in Context Rebuild, after everything else has given the
full standing picture.

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
