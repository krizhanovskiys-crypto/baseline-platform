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
- `docs/ai/` AI Context Rebuild workflow — `PROJECT_STATE.md`,
  `CTO_MEMORY.md`, `ACTIVE_SPRINT.md`, `AI_HANDOFF.md`, `PROMPT_START.md`,
  Repository Reality Check (Step 0), CTO Review (Step 3)
- Phase 3.1A — Empty State → Invite a Friend: every player-discovery
  empty state (Find Partner, Find Players for a Match) now offers a
  working "➕ Invite a Friend" Telegram share/deep-link button instead of
  a dead end; consolidated three near-duplicate empty-state text keys
  into one shared `player_discovery_no_results`
- Phase 3.1A follow-up: deep-link payload now carries the inviting
  player's telegram_id (`?start=invite_{telegram_id}`, format only — not
  parsed or acted on yet); empty-state copy updated to the approved
  wording ("🎾 Know someone who'd like to play?")
- Architecture Analysis (no code changed): traced all 6 player-discovery
  flows Entry→Service→Repository→Filter→Model; found the discovery
  *queries* were already Match Context–correct, and the actual
  player-profile dependency was one layer upstream, in Organize Match's
  creation wizard (`game.area` silently set from `player.home_area`,
  Court step scoped only to `player.preferred_courts`)
- **Match Discovery Refactor Phase 1** — Organize Match gained a
  mandatory Area step (default = organizer's home area, always
  changeable via the full Tennis Zone list); `game.area` now reflects
  that explicit choice, never silently the organizer's home_area. Court
  step shows one merged list per the chosen Area — favourite courts
  starred and listed first, then the rest of that zone's Court
  Registry, no duplicated/separate list. `find_players_for_match()`,
  `find_partners()`, and all repository/service discovery logic left
  untouched, per the approved Phase 1 scope.

## In Progress

Nothing currently in progress.

## Blocked

Nothing currently blocked.

## Next

**Sprint 11 — Match Discovery Refactor Phase 2** (repository
consolidation of `find_partners`/`find_players_for_match` — optional,
pure refactor, lower priority than Phase 1 was; no Strategy pattern).

Still undecided, to surface at the next Context Rebuild rather than
assume: whether the Players module Actions layer (suspend/reinstate —
`docs/BACKLOG.md` Epic 1 Phase 1) happens before or after Phase 2.
