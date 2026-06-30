# Sprint 7.0 — Available Matches — Architecture Specification

Status: Accepted (architecture frozen for Sprint 7.0)

This document is the implementation source of truth for Sprint 7.0. It captures
only the architecture approved during review. It is not a design proposal.

---

# 1. Goal

Available Matches lets a player browse matches that other organizers have
already created and that still need players, and join one directly — without
creating a new match and without waiting for an invitation. It is a second,
player-initiated path into a game (the first being Find Partner, which finds
people rather than matches). It serves the "find the right tennis partner"
and "make organizing a game easier" product goals.

---

# 2. User Flow

```
Home
→ Available Matches
→ Match Details
→ Join Match
→ Confirmation
→ Success
→ My Matches
```

---

# 3. Screen Flow

### Available Matches

Header:
```
🎾 Available Matches
{N} matches found
```

Each card shows:
- Match Type
- Level
- Date
- Time
- Area
- Court
- Players joined / required
- Status

Card button:
- View Details

Bottom keyboard:
- Filters
- Previous
- Next
- Home

### Match Details

Reuses the existing Match Details screen as-is (`match_details_keyboard`,
role = `"other"`). No changes to this screen's layout, text, or keyboard.
Its existing "Join Match" button (`match:join:{game_id}`) is the entry point
into the Join flow below.

### Join Confirmation

Text:
```
Join this match?

The host will be notified.
```

Buttons:
- Join
- Cancel (returns to Match Details)

### Success

Text:
```
✅ Successfully joined.

The host has been notified.

You can find this match in My Matches.
```

Buttons:
- My Matches
- Home

### Home entry point label

§2 requires a new entry point from Home. The main menu (`main_menu_keyboard`)
has no existing "Available Matches" button; one is added: `🎾 Available
Matches`, reusing the existing **Tennis data** emoji for consistency
(tennis-specific feature; `📋` is reserved for list/details-style screens).
Approved during architecture review.

---

# 4. Repository Layer

**Reused as-is (no changes):**
- `GameRepository.get_open_games(area)` — left untouched; still backs the
  REST API (`api/v1/games.py`). Out of scope for this sprint.
- `GamePlayerRepository.add_player_to_game(game_id, player_id, status)`
- `GamePlayerRepository.get_participation(game_id, player_id)`
- `GamePlayerRepository.count_committed_players(game_id)`
- `GamePlayerRepository.remove_player_from_game(game_id, player_id)`

**New method — `GameRepository.get_available_matches(...)`:**

Added alongside `get_open_games`, not replacing it.

Responsibilities:
- Return games with status `OPEN` or `PARTIALLY_FILLED`.
- Exclude games created by the requesting player (exclude organizer).
- Exclude games the requesting player already has an `ACCEPTED` /
  `CONFIRMED` `GamePlayer` row for.
- Apply filters: area, date, match_type, level.
- Apply sorting (§10).
- Apply pagination (§11).

Repository methods take only internal `player_id`. Never `telegram_id`.

No new `GamePlayerRepository` methods are required — joining, counting, and
rollback are fully covered by the existing methods listed above.

---

# 5. Service Layer

**Reused as-is:** `GameService` (existing instance, no constructor changes).

**New method — `get_available_matches(...)`:**
Thin pass-through to `GameRepository.get_available_matches(...)`, converting
`Game` rows to `GameRead` the same way every other `GameService` read method
does (`_game_to_schema`).

**New method — `join_match(game_id: int, player_telegram_id: int)`:**

Responsibilities, in order:
1. Resolve `player_telegram_id` → internal `player_id` (`PlayerRepository`).
2. Validate the player exists and has a complete profile.
3. Validate the game exists and its status is joinable (§6).
4. Validate the player is not the organizer and has no existing `ACCEPTED` /
   `CONFIRMED` participation row.
5. Add a `GamePlayer` row (`status=ACCEPTED`) via `add_player_to_game`.
6. Re-validate committed count against `required_players` (§7). If this
   join overfilled the match, remove the row just added and return
   `match_already_full`.
7. Advance lifecycle using the same pattern as
   `InvitationService._try_advance_lifecycle` (§6).
8. Notify the organizer (§13), best-effort.
9. Return the updated `GameRead`.

---

# 6. Lifecycle

Join allowed (game status):
- `OPEN`
- `PARTIALLY_FILLED`

Join forbidden (game status):
- `DRAFT`
- `FULL`
- `CONFIRMED`
- `IN_PROGRESS`
- `COMPLETED`
- `CANCELLED`
- `EXPIRED`

Implemented as an allow-list check (`status in {OPEN, PARTIALLY_FILLED}`),
not an enumerated deny-list, so it cannot miss a status.

Lifecycle advancement after a successful join reuses the exact pattern
already used by `InvitationService._try_advance_lifecycle` after
`InvitationService.accept()`:
- `OPEN → PARTIALLY_FILLED` on the first committed player.
- `PARTIALLY_FILLED → FULL` once committed count reaches `required_players`.
- Both transitions go through `MatchLifecycleService.transition()`.
- `InvalidTransitionError` is caught silently (another concurrent request
  already performed the same transition).

No new lifecycle states or transitions are introduced. The duplicated
advancement logic across `InvitationService` and `GameService` is an
accepted, documented tradeoff (see `docs/TECH_DEBT.md`, "Duplicate lifecycle
advancement after player joins") and is not resolved by this sprint.

---

# 7. Race Condition

No new locking mechanism is introduced. This reuses the existing project
approach (read-check-write), the same approach already used by
`MatchLifecycleService.transition()` and `InvitationService._try_advance_lifecycle`.

Behaviour when two players attempt to take the last slot at the same time:
1. Both transactions insert a `GamePlayer` row for their own player
   (different players → no primary-key conflict; both inserts succeed).
2. Each transaction re-reads the committed count via
   `count_committed_players` after its own insert.
3. The transaction whose insert leaves the count within `required_players`
   succeeds: it proceeds to lifecycle advancement and the Success screen.
4. The transaction whose insert pushes the count over `required_players`
   loses: its own `GamePlayer` row is removed via
   `remove_player_from_game`, and `join_match` returns the error key
   `match_already_full`. That player sees an error, not Success — they
   were never actually added.

This is the same level of protection already accepted elsewhere in the
codebase (correct under SQLite's single-writer serialization; not provably
race-free under PostgreSQL's concurrent transactions). The existing
`docs/TECH_DEBT.md` entry on atomic lifecycle transitions remains unchanged
and is not addressed by this sprint. `MatchLifecycleService` is not modified.

---

# 8. FSM

A new `AvailableMatchesStates` (`StatesGroup`) is required, following the
same single-state pattern as `FindPartnerStates`:

```
AvailableMatchesStates
    browsing = State()
```

Stored in FSM data:
- `current_page`
- `filters` (area, date, match_type, level)

`game_id` is never stored in FSM state — it always comes from `callback_data`,
consistent with every other browsing flow in the codebase.

---

# 9. Filters

Supported filters: Area, Date, Match Type, Level.

Defaults:
- Area: player's `home_area`
- Date: Today
- Level: player's `skill_level` ± 0.5
- Match Type: Any

Filters screen reuses existing `AREAS`, `SKILL_LEVELS` constants from
`texts.py` for option values.

---

# 10. Sorting

Priority order:
1. Same Area
2. Today
3. Earliest Date
4. Earliest Time
5. Closest Level

Distance-based sorting is reserved for a future release and is explicitly
out of scope for Sprint 7.0.

---

# 11. Pagination

- Page size: 5 matches per page.
- Navigation: Previous / Next buttons.
- Previous is disabled (omitted) on the first page; Next is disabled
  (omitted) on the last page — same convention as existing paginated
  keyboards in the codebase (e.g. `partner_card_keyboard`'s `show_next`).
- Current page is tracked in `AvailableMatchesStates` FSM data; page index
  also travels in `available:page:{page}` callback_data for direct navigation.

---

# 12. Callback Flow

| Callback | Trigger | Action |
|---|---|---|
| `available:start` | Home menu button | Load page 1 with default filters, show Available Matches |
| `available:details:{game_id}` | "View Details" on a card | Show existing (reused) Match Details screen |
| `available:filters` | "Filters" button | Show Filters screen |
| `available:page:{page}` | "Previous" / "Next" | Reload Available Matches at the given page |
| `match:join:{game_id}` | "Join Match" on Match Details (existing button) | Show Join Confirmation screen |
| `available:confirm:{game_id}` | "Join" on Join Confirmation | Call `GameService.join_match`, show Success or error |

`available:join:{game_id}` from the original draft is dropped — the existing
`match:join:{game_id}` callback (already wired on the reused Match Details
screen) is the real join entry point; no parallel callback is introduced.

The "Cancel" button on Join Confirmation reuses `available:details:{game_id}`
to return to Match Details. The Success screen's "My Matches" / "Home"
buttons reuse the existing `my_matches:back` / `menu:main` callbacks.

Every callback handler calls `callback.answer()`.

---

# 13. Notifications

Reuses the existing best-effort notification pattern (see `leave_match` in
`my_matches.py`): `callback.bot.send_message(...)` wrapped in `try/except
TelegramAPIError`, logged via `logger.warning` on failure, no retries,
delivery failure never blocks the join.

- Organizer receives: "Player joined your match."
- Joining player sees (in-app, Success screen): "Successfully joined."

---

# 14. Files

**Modified:**
- `backend/app/database/repositories/game_repository.py` — add
  `GameRepository.get_available_matches(...)`.
- `backend/app/services/game_service.py` — add `get_available_matches(...)`,
  `join_match(...)`.
- `backend/app/bot/handlers/my_matches.py` — replace the placeholder
  `match_join_handler` (`match:join:{game_id}`) with the real Join
  Confirmation screen, and add the `available:confirm:{game_id}` handler.
- `backend/app/bot/keyboards/keyboards.py` — add keyboards for the
  Available Matches list (card + bottom nav), Filters screen, Join
  Confirmation (Join/Cancel), and Success (My Matches/Home).
  `match_details_keyboard` is not modified.
- `backend/app/bot/states/states.py` — add `AvailableMatchesStates`.
- `backend/app/bot/texts.py` — add new keys for en/uk/ru: list header, card
  template, filters screen, join confirmation text, success text, organizer
  notification text, `match_already_full` error, and the new main-menu
  button label.
- `backend/app/bot/main.py` — register the new router
  (`dp.include_router(available_matches.router)`).

**New:**
- `backend/app/bot/handlers/available_matches.py` — entry point, list
  rendering, filters, pagination handlers (`available:start`,
  `available:details`, `available:filters`, `available:page`,
  `available:confirm`).

**Not modified (explicitly out of scope):**
- `backend/app/api/v1/games.py`
- `backend/app/database/models/game.py`
- `backend/app/services/match_lifecycle_service.py`

---

# 15. Tests

**Unit tests:**
- `GameRepository.get_available_matches` — status filter (excludes DRAFT,
  FULL, CONFIRMED, etc.), organizer exclusion, already-joined exclusion,
  area/date/match_type/level filters, sort order, pagination boundaries.
- `GameService.get_available_matches` — schema conversion.
- `GameService.join_match` — success path; each forbidden-status rejection;
  duplicate-join rejection; organizer-join rejection; lifecycle advancement
  (`OPEN→PARTIALLY_FILLED`, `PARTIALLY_FILLED→FULL`); overfill rollback
  returns `match_already_full` and leaves no orphaned `GamePlayer` row.

**Integration tests:**
- Two simulated concurrent `join_match` calls for the last slot of a match:
  exactly one succeeds, the other receives `match_already_full`, final
  committed count equals `required_players`.
- Full handler flow against the in-memory SQLite test DB: `available:start`
  → `available:details` → `match:join` → `available:confirm` → success,
  with `GamePlayer` and `Game.status` asserted in the DB.

**Manual E2E scenarios:**
- Browse Available Matches with default filters, page through results.
- Change filters, verify list updates.
- Open Match Details from a card, confirm it is the existing screen.
- Join an OPEN match → Success → match appears in My Matches.
- Join a match that becomes FULL between viewing and confirming → error
  shown, no false "Success".
- Attempt to view/join a match as its own organizer — not offered (excluded
  from the list).

---

# 16. Acceptance Criteria

Sprint 7.0 is complete when:
- A player can reach Available Matches from Home, browse, filter, and
  paginate through joinable matches.
- Match Details (existing screen) is unchanged and reused.
- A player can join an OPEN or PARTIALLY_FILLED match through Join
  Confirmation and land on Success.
- The organizer is notified (best-effort) on a successful join.
- Lifecycle advances using the existing `MatchLifecycleService` pattern,
  with no new transitions or statuses introduced.
- Simultaneous joins for the last slot never overfill a match; the losing
  request gets `match_already_full`.
- `get_open_games` and `api/v1/games.py` are untouched and the REST API
  behaves exactly as before.
- All tests in §15 pass; full `pytest` suite passes; bot dispatcher builds
  successfully.
