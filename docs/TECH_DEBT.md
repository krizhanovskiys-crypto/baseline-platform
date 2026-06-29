# Technical Debt Register

**Version:** 1.0  
**Owner:** Baseline Engineering  
**Status:** Active

All known technical debt items are tracked here. Each item must be reviewed before the sprint it is scheduled for. Unresolved items that affect user-facing behaviour must be documented in the Release Checklist before shipping.

---

## TECH-001

**Title:** Duplicated button trigger strings in handler modules

**Problem:**  
Each handler that responds to a ReplyKeyboard button defines its own `_TRIGGER_TEXTS` set with hardcoded emoji + label strings (e.g. `{"🔍 Find Partner", "🔍 Знайти партнера", "🔍 Найти партнёра"}`). These strings are a second source of truth that must be kept manually in sync with `texts.py`. When an emoji or label changes in `texts.py`, the matching `_TRIGGER_TEXTS` set must also be updated — a step that has already caused a routing regression (Find Partner broke after the UX-001 emoji audit).

**Impact:**  
Silent routing failures. A button press reaches no handler and the bot appears unresponsive. The failure is invisible without manual testing.

**Priority:** Medium

**Suggested solution:**  
Export a single canonical trigger constant from `texts.py` for each menu button (e.g. `BTN_FIND_PARTNER = {"🔍 Find Partner", ...}`) and import it directly into the handler. The set is then defined in exactly one place.

**Status:** Open

---

## TECH-002

**Title:** `create_invitation()` returns `None` for multiple distinct failure reasons

**Problem:**  
`InvitationService.create_invitation()` returns `None` in three structurally different cases: (1) game not found, (2) game in a non-invitable status, (3) a true duplicate invitation, (4) player already a `GamePlayer`. The calling handler maps all four to the same `inv_duplicate` toast ("Already invited."), which is factually wrong for cases 1–2 and caused a confirmed user-facing bug where a fresh match showed "Already invited" because the game was in `DRAFT` status.

**Impact:**  
Misleading error messages. Difficult to debug without inspecting logs. Wrong user expectation set for a recoverable state.

**Priority:** Medium

**Suggested solution:**  
Replace `None` with an explicit result type — either a `dataclass`/`NamedTuple` with a `reason` field (`"duplicate"`, `"wrong_status"`, `"not_found"`, `"already_participant"`) or a typed `enum`. The handler then maps each reason to the correct user-facing string.

**Status:** Open

---

## TECH-003

**Title:** No tracking of users who have blocked the bot

**Problem:**  
When `send_message()` raises `TelegramForbiddenError` (bot blocked) or `TelegramBadRequest` (chat not found), the failure is logged and the invitation remains in the database, but no state is written back to the `Player` record. On the next invite attempt the same player appears as a candidate and the same delivery failure occurs. There is no mechanism to surface blocked users to the organizer in advance or to exclude them from candidate lists.

**Impact:**  
Repeated silent delivery failures. Organizer invites a player, sees the delivery-failed alert every time, with no path to resolution.

**Priority:** Low (post-MVP)

**Suggested solution:**  
Add a `bot_blocked: bool = False` column to `Player`. Set it to `True` when `TelegramForbiddenError` is caught in `fpm_select`. Reset it to `False` when the user sends `/start` (they have unblocked the bot). Add `Player.bot_blocked.is_not(True)` to `find_players_for_match` query. Requires a migration.

**Status:** Open

---

## TECH-004

**Title:** Emoji usage not fully centralised

**Problem:**  
The emoji system is defined as a semantic table in `CLAUDE.md` (one meaning per emoji) but individual emoji characters are embedded directly in `texts.py` string literals throughout. There are no named constants. Changing the emoji assigned to a concept (e.g. renaming 📨 to a different glyph) requires a full-text search and replace across the entire `_TEXTS` dict, and any missed occurrence creates an inconsistency.

**Impact:**  
Risk of divergence between the documented emoji system and the live strings. Past audit (Polish 6.1.1) required manual inspection of every key across three languages.

**Priority:** Low

**Suggested solution:**  
Define emoji constants at the top of `texts.py` (e.g. `_E_INVITE = "📨"`) and reference them in string literals via f-strings or `.format()`. The semantic table in `CLAUDE.md` then maps concept → constant name, not concept → raw character.

**Status:** Open

---

## TECH-005

**Title:** Callback data strings generated inline at every call site

**Problem:**  
Callback data strings such as `f"fpm:start:{game_id}"`, `f"match:open:{game_id}"`, `f"inv:accept:{inv_id}"` are constructed with f-strings directly in keyboard builder functions and parsed with `str.split(":")` in handlers. There is no single source of truth for the format. If a prefix or structure changes, both the keyboard builder and every handler that parses it must be updated in sync.

**Impact:**  
Fragile coupling between keyboards and handlers. A typo in a prefix silently breaks routing (callback goes unhandled, button appears stuck). No IDE support for finding all usages.

**Priority:** Low

**Suggested solution:**  
Introduce a `CallbackData` factory using `aiogram.filters.callback_data.CallbackData` (Aiogram 3.x built-in). Each callback type is declared once as a typed dataclass; `pack()` generates the string and `filter()` / `unpack()` parse it. Eliminates all manual `split(":")` calls.

**Status:** Open

---

## TECH-006

**Title:** Race condition in game status transitions on PostgreSQL

**Problem:**  
`MatchLifecycleService.transition()` uses a read-check-write pattern: it reads the current status, validates the transition is allowed, then writes the new status in a separate statement. Under concurrent requests on PostgreSQL this creates a TOCTOU (time-of-check / time-of-use) window. Two simultaneous acceptances could both read `OPEN`, both pass the `OPEN → PARTIALLY_FILLED` check, and both attempt the same transition.

**Source:** `match_lifecycle_service.py:64` — `# TODO: Replace read-check-write with conditional UPDATE before moving to PostgreSQL.`

**Impact:**  
Currently masked by SQLite's serialised writes. Will cause duplicate transitions or `InvalidTransitionError` under concurrent load on PostgreSQL.

**Priority:** Low (pre-PostgreSQL migration)

**Suggested solution:**  
Replace the read-check-write with a single conditional `UPDATE games SET status = :new WHERE id = :id AND status = :expected` and check `rowcount == 1` to confirm the transition was applied. No race window.

**Status:** Open — flagged in source via `TODO` comment

---

## TECH-007

**Title:** Investigate intermittent Cancel Match issue on newly created OPEN doubles matches

**Problem:**
During manual testing, pressing "Cancel Match" on a freshly created OPEN doubles match (organizer only, 1/4 players) produced the error "This match cannot be cancelled." The issue was observed once and is not currently reproducible. Service layer (`GameService.cancel_match`), lifecycle transitions (`OPEN → CANCELLED` is valid), and all 169 automated tests pass. Runtime debug logging was added but the repro attempt did not yield log output before the investigation was paused.

**Impact:**
Low — organizer cannot cancel a match. Workaround: none identified. Frequency: not confirmed; single observation.

**Priority:** Low

**Suggested solution:**
If the issue reappears, reproduce with the following instrumentation in place before making any code changes:
1. Add `logger.warning("[CANCEL_DEBUG] game_id=%s status=%s", game_id, game.status.value)` at `game_service.py` before `MatchLifecycleService.transition()`.
2. Add `logger.warning("[LC_DEBUG] current=%r allowed=%s", current, [s.value for s in allowed])` at `match_lifecycle_service.py:70`.
3. Confirm which handler fires: `match_cancel_handler` (`match:cancel:{id}`) in `my_matches.py` or `cancel_match` (`cancel_match:{id}`) in `confirm_match.py`.
4. Check `game.status` raw DB value via `sqlite3 baseline.db "SELECT id, status FROM game WHERE id = <id>"`.

**Status:** Investigate — observed once, not reproducible, no code changes until confirmed

---

## TECH-008

**Title:** Optimize lazy expiration for large datasets

**Problem:**
`GameService.get_my_upcoming_matches()` calls `_expire_stale()` with no `game_id`, which queries all pre-start matches (OPEN, PARTIALLY_FILLED, FULL, CONFIRMED) and checks each one individually. As the match table grows this becomes a full table scan on every My Matches request.

**Impact:**
Acceptable at MVP scale. Will become a latency problem once the number of concurrent open matches is large.

**Priority:** Low

**Suggested solution:**
Replace the global sweep in `get_my_upcoming_matches()` with one of:
- A targeted query that adds a `date < today OR (date = today AND time < now)` filter directly in `get_expirable_matches()` to limit returned rows to genuinely stale games.
- A background job (APScheduler, Celery beat) that runs the expiry sweep on a fixed interval (e.g. every 15 minutes), removing the per-request overhead entirely.

The `expire_if_stale()` method on `MatchLifecycleService` remains the single transition point regardless of which approach is chosen.

**Status:** Open

---

*Items without a source `TODO`/`FIXME` annotation are tracked here only. Items with a source annotation are listed under both the code comment and this register.*

---

## Related documents

| Document | Purpose |
|---|---|
| [`docs/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | A release is blocked until open debt is documented or resolved |
| [`CLAUDE.md`](../CLAUDE.md) | Engineering rules and architecture constraints that inform debt assessment |
