# Baseline Product Decisions

**Purpose:** the single source of truth for *approved and shipped*
product decisions — what was decided and why, not the vision or the
rules.

**What belongs here:** a decision that has actually been implemented,
with its reasoning and where it shows up in the code. Entries are
attributed to the sprint in which they were approved; once a decision
ships, cross-reference the code/doc that implements it so this file stays
verifiable rather than aspirational.

**What must never be duplicated here:** long-term direction (→
`docs/VISION.md`), the phased future plan (→ `docs/ROADMAP.md`),
mandatory engineering rules (→ `docs/engineering/CONSTITUTION.md`), a
decision that hasn't been accepted yet (→ discuss it, don't pre-write it
here — an entry here asserts something is *done*, not proposed), or ideas
intentionally out of scope (→ `docs/IDEAS.md`).

---

## Baseline helps users find games, not just players

**Decision:** The product's core loop is centered on matches (organized,
joinable, browsable), not a player directory. Find Partner exists to help
start a game, not as a standalone social/browse feature.

**Why:** Matches are the concrete, schedulable unit of value ("play tennis
Tuesday at 6pm"), and CLAUDE.md's UI-language rule ("Users **organize
matches** and **invite players**") already encodes this — the product
vocabulary is match-first.

**Where it shows up in the code:**
- `docs/VISION.md`, Pillar 1 "Find a Match" — "Players should find a game
  in under 30 seconds."
- `backend/app/bot/handlers/organize_match.py`, `available_matches.py`,
  `find_players_for_match.py` — match creation/browsing/joining are
  first-class flows, each with their own wizard/list.
- Find Partner (`find_partner.py`) exists alongside these, not instead of
  them, and its own product framing is "find someone to start a match
  with," not general social browsing.

---

## Tennis Zones

**Decision (Sprint 10.3 Phase 2):** Baseline does not use administrative
city districts (the old `AREAS` list: Downtown, North York, Etobicoke,
Mississauga, Scarborough, Richmond Hill, Markham). It uses **Tennis
Zones** — groupings that reflect how players actually talk about where
they play, spanning the Greater Toronto Area:

- Downtown
- West Toronto / Etobicoke
- North York
- Scarborough
- Mississauga
- Vaughan
- Markham / Richmond Hill
- Oakville / Burlington

**Why:** Administrative boundaries don't match how tennis players describe
"where they play" — the zone list merges/relabels districts (e.g. Markham
+ Richmond Hill into one zone) and adds coverage the old list lacked
(Vaughan, Oakville/Burlington).

**Where it shows up in the code:** `TENNIS_ZONES` in
`backend/app/data/courts.py`, derived from `COURTS_BY_ZONE.keys()` — one
list is the single source of truth for both "what is a zone" and "what
courts are in it." `area_keyboard()` in `keyboards.py` renders this list
under callback prefixes like `area:`, `settings_area:`,
`fp_smartfilter_area:`, and `available:filter:area:` — the underlying
`Player.home_area` column and its Python identifiers were **not** renamed
(no migration required); only the displayed values and their copy
("Tennis Zone" instead of "Home Area") changed.

**Backward compatibility:** a player's `home_area` saved before this
sprint (e.g. `"Etobicoke"`) keeps working — matching is exact-string
equality, unaffected by the zone list's contents — but will no longer
match a current zone button until the player re-selects one via Edit
Profile. This is intentional: no forced migration, no data loss, no crash.

---

## Court Registry

**Decision (Sprint 10.3 Phase 2):** Real public tennis courts are
maintained in a dedicated registry, grouped by Tennis Zone, instead of
being hardcoded as a single flat list inside a handler or keyboard.

**Why:** The previous `COURTS` list (`backend/app/bot/texts.py`, now
removed) was 7 fixed courts with no zone awareness, shared identically by
onboarding, Edit Profile, and Find Partner's Smart Filter — impossible to
scale past a handful of entries without becoming an unusable single
screen, and with no way to express "this court is in that zone."

**Design:**
- `backend/app/data/courts.py` — `COURTS_BY_ZONE: dict[str, list[str]]` is
  the single source of truth; `TENNIS_ZONES` and `get_courts_for_zone()`
  are derived from it. The module is pure data + lookup (no ORM, no
  session), so it is a drop-in replacement target for a future database
  Court model — callers depend only on `get_courts_for_zone(zone) ->
  list[str]`, never on the dict's internal shape.
- Each zone carries 7–9 real public courts, sourced from municipal
  parks-and-recreation listings (not invented).
- Flow, onboarding: **Select Tennis Zone → that zone's courts (+ any
  Custom Courts already selected) → ➕ Add my own court**. The zone step
  is unavoidable here since the player has no Home Area saved yet.
- Flow, Edit Profile → Favourite Courts (revised after a second product
  review — see "Product Review before Commit"): **straight to the
  player's Home Area's courts** — no separate zone picker. Asking the
  player to pick a Tennis Zone here was found to be a redundant step: the
  player's Home Area (`Player.home_area`, set via Edit Profile's own
  dedicated "Area" field) already answers "which zone," so
  `settings_change_courts` in `backend/app/bot/handlers/profile.py` opens
  `courts_keyboard(lang, player.home_area, ...)` directly. Changing which
  zone's courts appear here happens **only** by changing Home Area via
  the "Area" field — there is no independent zone browser inside
  Favourite Courts anymore. A player who wants a favourite court outside
  their home zone still can — via "➕ Add my own court" (Custom Courts),
  not by re-picking a zone. Backward compatibility: a player with no
  saved `home_area` (nullable field; shouldn't happen once onboarding is
  complete, but handled defensively) falls back to the standalone Tennis
  Zone picker (`SettingsStates.choose_courts_zone`) so they're never stuck.
- Flow, Find Partner Smart Filter: unchanged — reuses the same zone-scoped
  court picker, scoped to whichever zone *that* filter is currently
  searching (its own "Area" filter, independent of the player's profile
  Home Area, since a search can legitimately target a different zone).
  See "Custom Courts" below for the add-your-own-court decision in detail.

**Migration path to a database-backed registry:** replace
`COURTS_BY_ZONE`/`get_courts_for_zone()` with repository-backed
equivalents of the same signature; no caller (`keyboards.py`, handlers)
would need to change.

---

## Custom Courts

**Decision (Sprint 10.3 Phase 2):** A player can always add a court the
Court Registry doesn't have, via "➕ Add my own court" — replacing the old
flat list's "Other" item, which stored a literal, non-descriptive `"Other"`
string. The registry is deliberately not exhaustive (real courts, curated,
not every court that exists), so this is the escape hatch, not a fallback
for missing data quality.

**Storage:** custom courts live in the existing `Player.preferred_courts`
field (JSON-encoded text column) — no new table, no new column, no
migration. `PlayerService.find_partners` does plain string
set-intersection on `preferred_courts` and has no awareness of the
registry at all, so registry courts and custom courts rank identically —
adding the registry introduced zero risk of matching regressions
(verified in `tests/test_find_partner_service.py::
test_matching_works_with_registry_and_custom_courts_mixed`).

**UX (revised after product review, same sprint):** the first
implementation only confirmed a custom court via a text message
("✅ Court added successfully") — the player had to trust it was saved,
with no visual confirmation in the court list itself. Product review
flagged this as a weaker experience than seeing the court checked
immediately, matching how a registry court behaves. Fixed by extending
`courts_keyboard(lang, zone, selected)`: any already-selected court not
in `zone`'s registry list renders as an extra ✅-checked button under a
"── Custom Courts ──" divider, below the zone's registry courts —

```
☐ Ramsden Park      ☑ Trinity Bellwoods
☐ Stanley Park
── Custom Courts ──
☑ High Park Bubble
➕ Add my own court
✅ Done
```

It toggles through the exact same `court_toggle:{court}` callback as a
registry court, so removing a custom court is just tapping it again — no
new FSM state, no separate handler. `onboarding_court_toggle`,
`settings_court_toggle`, and `fp_smartfilter_court_toggle` already
operated on the flat selection list by court name, so this was a
rendering-only change confined to `keyboards.py`. Identical behavior in
onboarding, Edit Profile, and Find Partner's Smart Filter — one keyboard
function, three callers.

**Divider wording:** "Custom Courts," not "Your Courts" — chosen so the
label still reads correctly once the registry itself grows categories
(Public Courts, Private Clubs, Indoor Facilities, Bubble Courts, etc.);
"Custom" specifically means "not a registry entry," which "Your Courts"
would not have kept communicating once registry courts are also, in a
sense, "yours."

**Future Enhancement (not scheduled, no implementation now):** in a
future version, users should be able to select favourite registry courts
from multiple Tennis Zones without those extra-zone courts being treated
as custom courts. This is intentionally postponed — Court Registry v1.0
deliberately keeps Favourite Courts scoped to the player's Home Area (see
"Court Registry" above), and a court from another zone is, for now,
reachable only via "➕ Add my own court." Revisit once there's a concrete
need for browsing/selecting registry courts across zones in one flow.

---

## Development workflow

Established and enforced via `CLAUDE.md` and
`docs/engineering/CONSTITUTION.md` (see that file for the authoritative,
MUST/MUST NOT version). Summary:

1. Understand the task, read only what's needed, implement only what was
   asked — no adjacent refactors, no unrelated cleanup.
2. Model → Repository → Service → Handler for every new domain; handlers
   never contain business logic.
3. Every feature ships with tests (including a regression test for bug
   fixes); the full `pytest` suite must pass before reporting done.
4. Verify the bot dispatcher builds for any bot-facing change.
5. Present modified files + test results + risks; wait for explicit human
   review.
6. Commit only after approval — never automatically, never mid-task.

---

## Product Review before Commit

**Decision:** implementation being functionally correct and fully tested is
not sufficient to commit — a product/UX review pass happens first, and its
feedback is applied *before* the commit, not scheduled as a follow-up,
unless the requester explicitly chooses to defer it.

**Why:** this is where UX regressions — and over-corrections — get caught
cheaply. Sprint 10.3 Phase 2 shipped a working, tested Court Registry;
product review went through three rounds before commit: (1) confirming
the custom-court flow needed to show the added court checked immediately,
not just confirm it via text; (2) confirming Edit Profile's zone picker
was never silently defaulting to the home zone; and (3) — after living
with round 2's answer — recognizing that *always* asking for a zone was
itself a redundant step once a Home Area is already saved, since the
dedicated "Area" field already answers that question. Round 3 reversed
part of round 2's confirmed behavior; that's a legitimate outcome of
review, not a mistake to avoid — a decision confirmed as "working as
intended" can still be revisited once its real usage is considered. See
"Custom Courts" and "Court Registry" above for the resulting design.

**How it works in practice:**
1. Implementer presents modified files, root cause (if any), test results,
   and a manual testing checklist — never just "done."
2. Reviewer may ask product/UX clarifying questions distinct from code
   review — confirming flows match intent, not hunting for bugs.
3. If review surfaces a gap, it's fixed inline (new/updated tests
   included) and the full suite re-run, *before* commit — not left as
   scored tech debt unless the reviewer explicitly says to defer it.
4. Commit happens only after the reviewer states approval explicitly.

---

## UX principles approved during Sprint 10

- **One screen per concept.** Sprint 10.3 Phase 1 removed a duplicate "My
  Matches" screen that had drifted from the real one (different service
  method, hardcoded player count, no Match Details actions). The rule
  going forward: a feature must have exactly one canonical screen,
  reachable identically regardless of entry point (main menu, a
  just-completed action, or a link from another screen) — see
  `backend/app/bot/handlers/my_matches.py` and the removal of
  `organize_match.py::om_my_matches`.
- **A created resource must be immediately usable.** The My Matches fix's
  root cause was `GameService.create_game()` leaving a match in `DRAFT`
  and relying on the caller to remember to open it. The principle: a
  service that creates something visible/actionable must leave it in a
  usable state itself — that invariant must not depend on every future
  caller remembering an extra step.
- **Never invent data presented as real.** When populating the Court
  Registry, only real, sourced public courts were used — no placeholder
  or invented court names, even to hit a round count per zone.
- **No forced migrations for UI/vocabulary changes.** Tennis Zones
  replaced the old Area list's values without a database migration or
  forced re-selection — old data keeps working, and a player only sees
  the new vocabulary when they next touch that field.

---

## Admin Center Architecture

**Decision (Sprint 11):** Admin Center is a standalone administrative
product inside Baseline — the umbrella decision the rest of this section
and the narrower entry below both fall under.

- Administrative functionality must never duplicate business logic.
- Admin handlers may only access domain functionality through existing
  Services.
- Administrative permissions are completely independent from Player.
- `OperatorPermission` is the only source of operator authorization.
- Authentication (PIN/session) and authorization (permissions) remain
  separate responsibilities.
- Admin Center is implemented as modular packages:

  ```
  handlers/admin/
      auth.py
      common.py
      players.py
      matches.py
      courts.py
      tournaments.py
      coaches.py
      testing.py
      system.py
  ```

  This modular architecture is mandatory for all future Admin Center
  features.

**Why:** Admin Center is the foundation for a growing list of future
domains (Players, Matches, Courts, Tournaments, Coaches, System), each
touching real player/match data through an operator who is not that
data's owner. Every principle above closes a specific risk that shape of
feature creates: duplicated business logic would mean a bug fixed in
`GameService` but not in whatever an admin handler reimplemented;
permissions coupled to `Player` would tie operator access to profile-
completeness rules that have nothing to do with operating the platform;
authentication and authorization being the same responsibility would
make it harder to add 2FA or per-operator PINs later without also
touching role logic.

**Where it shows up in the code:** `backend/app/services/permission_service.py`
(authorization only), `backend/app/services/admin_session_service.py`
(authentication/session only — never merged into `PermissionService`),
`backend/app/database/models/operator_permission.py` (no `is_admin` or
`role` field was added to `Player`), and every handler in
`backend/app/bot/handlers/admin/` calling into `PlayerService`,
`GameService`, `MatchLifecycleService`, etc. rather than querying a
repository directly. See `docs/ARCHITECTURE.md` §11 for the full module
layout rule.

---

## Admin Center is a package, not a growing file

**Decision (Sprint 11 Phase 2.1):** every Admin Center capability —
Players, Matches, Courts, Tournaments, Coaches, System, Testing — is its
own module under `backend/app/bot/handlers/admin/`, registered in that
package's `__init__.py`. `dev.py` (the original hidden-command handler)
was retired the same sprint it was introduced, before a second tool
could be added to it. This is the modular-packages principle from
"Admin Center Architecture" above, in more implementation detail.

**Why:** Admin Center is the foundation for a growing list of future
domains (Sprint 11's own architecture proposal lists Tournaments,
Coaches, and System tools as later phases). Letting every one of those
land in a single file was the exact shape of problem CLAUDE.md's
architecture rule already exists to prevent for the rest of the
bot (`handlers/` is one file per feature) — this decision makes the same
discipline explicit for Admin Center specifically, before the file had a
chance to grow past two tools.

**Where it shows up in the code:** `backend/app/bot/handlers/admin/` —
`common.py` (shared `authorized_role()`/`lang_for()`), `auth.py` (the
access flow), `testing.py` and `system.py` (today's tool modules). See
`docs/ARCHITECTURE.md` §11 for the full module layout rule and the
future module list.

---

## Every Admin Center record module has the same shape

**Decision (Sprint 11 Phase 3.0):** Players, Matches, Courts, Coaches,
and Tournaments — every Admin Center module built around a record type,
not a utility like Testing or System — follows one fixed structure:
Search → Browse → Details → Actions, in that order, built the same way
every time.

**Why:** `players.py` (Search Player, Browse Players, Player Details)
was built first and, only after the fact, was recognized as a pattern
worth locking in before Matches, Courts, Coaches, and Tournaments each
invent their own navigation shape independently. A year from now, a
contributor opening `matches.py` for the first time should already know
its structure from having read `players.py` — that's the entire value of
this rule, and it only holds if it's written down now, while there's
still exactly one module to compare against.

**Where it shows up in the code:** `docs/ARCHITECTURE.md` §12 has the
full structural rule — the Search three-way branch (one match/many
match/no match), Browse's fixed 20-per-page + nearest-valid-page
behavior, Details as read-only, and Actions as a later layer that always
calls into that record's existing domain service
(`PlayerService`/`GameService`/`MatchLifecycleService`/...) rather than
a new mutation path. `players.py` has no Actions yet — that's
`docs/BACKLOG.md` Epic 1's own Phase 1 item (player suspend/reinstate)
— but Search/Browse/Details are already shaped so Actions attaches to
Details without restructuring anything built in Phase 3.0.

---

## User-entered text must be escaped for its parse_mode before display

**Decision (Sprint 11 Phase 3.0):** any value that originated as free-form
user input — `Player.first_name`, `Player.username`, a custom court
name, and (once built) a tournament name, coach bio, club name, or any
other user-entered text — MUST be escaped for the message's `parse_mode`
before it is interpolated into a Telegram message. This applies to every
current and future screen, not only Players.

**Why:** Player Details (Phase 3.0) crashed with `TelegramBadRequest:
can't parse entities` for any player whose `first_name` or `username`
contained a single, unpaired Markdown special character — which is the
*ordinary* case, not an edge case: Telegram usernames routinely contain
underscores (`john_doe`), and Legacy Markdown reads a lone `_` as an
unterminated italic span. This is a security/stability rule, not a
one-off bug fix — any screen that renders user-entered text through
`parse_mode="Markdown"` (or `MarkdownV2`/`HTML`) without escaping it is
one ordinary underscore away from crashing for a real user, and every
planned future module introduces new free-text fields with the identical
risk (a tournament name, a coach bio, a club name — all as unrestricted
as `first_name` already is).

**Where it shows up in the code:** `backend/app/bot/handlers/admin/players.py`'s
`_md()` wraps aiogram's own `aiogram.utils.markdown.markdown_decoration.quote()`
— aiogram is already a project dependency, so this is reuse, not a new
escaping library. Applied to `first_name`, `username`, and custom court
names in both `_format_details()` and `_format_browse_row()`. `_md()`
currently lives in `players.py` since it's the only module using it
today; the moment a second module (Matches, Tournaments, Coaches, ...)
needs the same escaping, it MUST be promoted to a shared location (e.g.
`admin/common.py`, alongside `authorized_role()`/`lang_for()`) rather
than reimplemented per module.
