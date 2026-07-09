# Sprint History — Sprint 11

**Purpose:** archived detail for Sprint 11 and Sprint 11.1. Moved here
from `docs/ai/PROJECT_STATE.md`'s "Completed Major Features" list
(Sprint 13.1 documentation refresh) so that file can stay a concise
current-state snapshot instead of a growing narrative. No information
was removed in the move.

---

## Admin Center — Auth Foundation (Sprint 11 Phase 2.1)

`OperatorPermission`, `PermissionService`, `AdminSessionService` (PIN,
session, lockout, audit log).

## Admin Center Dashboard (Sprint 11 Phase 2.2)

Live Environment/Version/Uptime/stats, the permanent root screen.

## Admin Center Players Module (Sprint 11 Phase 3.0)

Search/Browse/Details — the reference implementation for all future
record modules.

## AI Context Rebuild Workflow (Sprint 11)

`docs/ai/*`, `PROMPT_START.md`, Repository Reality Check, CTO Review.

## Empty State → Invite a Friend (Sprint 11 Phase 3.1A)

Every player-discovery empty state (Find Partner, Find Players for a
Match) offers a working Telegram share/deep-link "➕ Invite a Friend"
button instead of a dead end; consolidated three near-duplicate
empty-state text keys into one shared `player_discovery_no_results`.
Deep-link payload carries the inviting player's telegram_id
(`?start=invite_{telegram_id}`) — not parsed or acted on yet, format
only, ahead of future referral tracking.

## Match Discovery Refactor Phase 1 (Sprint 11)

Organize Match gained a mandatory Area step
(`OrganizeMatchStates.choose_area`): defaults to the organizer's home
area via "✅ Use my area", but "✏️ Change area" opens the full Tennis
Zone list — the organizer's home_area is no longer silently forced
onto `game.area`. The Court step now shows one merged list scoped to
the chosen Area — favourite courts within that zone starred and
ordered first, followed by the rest of that zone's Court Registry, no
separate/duplicated list. `find_players_for_match()`, `find_partners()`,
and every other discovery query were untouched — analysis found the
query layer was already Match Context–correct; only match *creation*
needed fixing.

## Tournament Stabilization Phase 1 (Sprint 11.1)

Admin/Coach's own Tournament Details screen now runs the same lazy
`check_and_auto_close()` + Registration Closed Notification the
player-facing Details screen already did; previously it never did, so
a tournament whose deadline had passed stayed REGISTRATION_OPEN
indefinitely unless a *player* happened to open it. Verified Coach
tournament creation was confirmed architecturally correct against a
correctly-migrated schema — the reported failure was TECH-010's schema
drift (a dev database missing `players.is_verified_coach`), not a code
defect.

**Task 1 (Verified Coach couldn't create tournaments)** — found to be
environmental, not a code bug: TECH-010's schema drift left the dev
database missing `players.is_verified_coach`. Confirmed via a
controlled test against a correctly-migrated schema that `/dev`
routing, `can_create_tournament()`, and `tourn_create_start` are all
already correct for a genuine Coach-only account. No permission
architecture changed.

**Task 2 (Registration Deadline didn't auto-close)** — real bug:
`admin/tournaments.py`'s own Details screen never called
`check_and_auto_close()`, only the player-facing one did. Fixed by
wiring the same lazy check into the Admin/Coach Details screen.

**Task 3 (Registration Closed notification)** — fixed as a direct
consequence of Task 2's fix; every other close trigger already
notified correctly. No notification logic redesigned.

4 new regression tests (`tests/test_tournament_stabilization.py`):
Verified Coach can create / Regular Player cannot (both through the
real handlers, not just the service check), auto-close+notify via
Admin Details, manual-close notifies every registrant exactly once.

**Verified** on a clean schema; **pending** validation on the real
development database specifically after TECH-010 recovery is actually
carried out there — not to be treated as fully closed end-to-end until
that happens. (TECH-010 recovery is now supported by
`scripts/schema_recovery.py` — see `docs/ai/history/Sprint-12.md`.)
