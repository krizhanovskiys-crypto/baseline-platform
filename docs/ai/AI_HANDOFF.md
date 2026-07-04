# AI Handoff Log

**Purpose:** updated at the end of every sprint, newest entry first.
Each entry is what a new AI session needs to pick up work with zero
chat history — what changed, what was decided, what's blocked, what's
next. Read last in Context Rebuild, after everything else has given the
full standing picture.

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
