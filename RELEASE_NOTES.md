# Baseline Release Notes

**Purpose:** the single log of what has actually shipped, in the order it
shipped. If a feature is listed here, it is live in the product today.

**What belongs here:** completed work only, grouped by sprint, newest
first — New / Improved / Removed / Internal, matching each sprint's own
scope.

**What must never be duplicated here:** future/planned work (→
`docs/ROADMAP.md`), the reasoning behind a decision (→
`docs/PRODUCT_DECISIONS.md`), or open technical debt (→
`docs/TECH_DEBT.md`). This file records *that* something shipped, not
*why* it was designed that way.

---

## Sprint 10.4 — Environment Separation & UX Polish

### New

* Separate development/production configuration — `ENV=development` /
  `ENV=production` selects `.env.dev` / `.env.production`; unset `ENV`
  keeps loading the original `.env` unchanged
* Court Registry court list is now scoped to the player's Home Area when
  editing Favourite Courts — no redundant Tennis Zone re-selection
* Cancel Match confirmation step; cancelling now notifies every
  participant, not just the organizer
* Organize Match wizard shows a step progress indicator on every screen

### Improved

* Unified the two independent Cancel Match code paths into one flow
* Main Menu emoji made unique per button (no shared 🎾 between Organize
  Match and Available Matches)
* "Available Now" renamed to "I'm Available"
* Header wording and formatting standardized across Organize Match,
  Settings, and Find Partner's Search Mode screen
* "Tennis Zone" UI wording reverted to "Area" (internal naming —
  `TENNIS_ZONES`, `COURTS_BY_ZONE`, `home_area` — unchanged)
* View Roster's Back button now returns to Match Details, not the Main
  Menu
* "Profile incomplete" now shows the same message used by every other
  profile-completeness guard

### Internal

* `docs/ARCHITECTURE.md` added as the technical HOW reference
* `docs/PRODUCT_DECISIONS.md` trimmed to accepted decisions only

---

## Sprint 10.3 — My Matches Fix & Court Registry v1.0

### New

* Court Registry: real public tennis courts grouped into 8 Tennis Zones
  (`backend/app/data/courts.py`), replacing the old flat 7-court list
* Custom courts — "➕ Add my own court" for any court not in the registry,
  stored in the existing `preferred_courts` field (no new table)
* Edit Profile Courts flow: Select Tennis Zone → that zone's courts →
  add your own

### Fixed

* A newly created match is now immediately visible in My Matches —
  `GameService.create_game()` opens the match itself instead of relying
  on each caller to remember an extra step
* Removed a duplicate "My Matches" screen that had drifted from the real
  one (different service method, hardcoded player count, no actions)

---

## Sprint 10.2 — Migration Repair

### Fixed

* Repaired the initial Alembic migration, which only ever ran an
  `ALTER TABLE` and never created the base tables — `alembic upgrade head`
  now works on a clean database

---

## Sprint 10.1 — Analytics Foundation

### New

* `analytics_events` table and `backend/app/insights/` package
  (`track_event(user_id, event, metadata=None)`)
* Automatic tracking for `user_registered`, `profile_completed`,
  `find_partner_opened`, `game_created`

---

## Sprint 7.3 — UI Unification

### Improved

* Unified card and button presentation across every Sprint 7 screen

---

## Sprint 7.2 — Find Partner Smart Filter

### New

* Find Partner Search Mode
* Smart Filter

### Improved

* Reused Filter UX
* Temporary search filters
* No changes to matching algorithm

---

## Sprint 7.1 — Profile UX Redesign

### New

* Redesigned Profile UX
* New Edit Profile experience
* Spoken Languages support

### Improved

* Automatic profile saving
* Profile simplified

---

## Sprint 7.0 — Available Matches

### New

* Browse Open Matches — paginated list with Area / Date / Level / Match
  Type filters
* Join Match

---

## Sprint 6.1 – 6.5 — My Matches & Match Lifecycle Completion

### New

* My Matches (upcoming matches list)
* Match Details screen, role-based actions (organizer / participant /
  other)
* Leave Match
* Cancel Match (pre-start)
* Lazy match expiration — a past-dated pre-start match transitions to
  Expired the next time it's read; no background job

### Improved

* Split invitation handling out of the match flow into its own domain

---

## Sprint 5.1 – 5.3 — Match Lifecycle State Machine

### New

* Match Lifecycle state machine (`MatchLifecycleService`) — the sole
  authority over `Game.status`, with an explicit valid-transitions table
* Automatic lifecycle transitions as players accept/join
* Organizer Confirmation flow

---

## v0.3.0

### New

* Player onboarding
* Player profile
* Settings
* Find Partner
* Organize Match
* Find Players for a Match
* Match invitations
* Accept invitation
* Decline invitation
* Automatic match player count updates
* Ukrainian, English and Russian localization

### Improved

* Simplified terminology ("Invite" instead of "Select")
* Streamlined match organization flow
* Cleaner user interface

### Removed

* Rating from all user-facing interfaces — Baseline does not use player
  ratings; see `PRODUCT.md`'s Non-Goals

### Internal

* New Invitation domain
* Invitation model
* Invitation repository
* Invitation service
* Invitation handlers
* Alembic migration support
* Standardized architecture (Model → Repository → Service → Handler)
