# Baseline Product Decisions

This document is the single source of truth for approved product decisions.
It complements `docs/VISION.md` (long-term direction), `docs/ROADMAP.md`
(phased plan), and `docs/engineering/CONSTITUTION.md` (mandatory engineering
rules) — this file records **what was decided and why**, not the vision or
the rules.

Entries are dated and attributed to the sprint in which they were approved.
Once a decision ships, cross-reference the code/doc that implements it so
this file stays verifiable rather than aspirational.

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

## "🎾 On Court Now" is a separate workflow

**Status: referenced during Sprint 10 planning; not yet fully specified in
this repository.**

The current shipped feature is "🔥 Available Now" (`btn_available_now`,
`backend/app/bot/handlers/available_now.py`): a player marks themselves
available for the next 2 hours and appears in a list other players can
browse. "🎾 On Court Now" was raised as a **distinct** concept from this —
the working assumption is that it represents a player signaling they are
*currently mid-session on a specific court* (a live/real-time state) rather
than *available to be contacted for the next 2 hours* (Available Now's
existing semantics).

This entry is intentionally left without implementation detail (target
states, whether it replaces or supplements Available Now, court-registry
integration) because that detail wasn't established in the sessions this
document was compiled from. Fill in and re-date this section from the
source planning conversation before it is treated as a build-ready spec —
per the Engineering Constitution, "Documentation updates MUST NOT invent
scope beyond what was actually built."

---

## Coach Role architecture

**Status: partially implemented at the data layer; role/permission system
not yet built.**

What exists today:
- `Player.level_source` (`backend/app/database/models/player.py`) —
  `"self_rated"` or `"coach_verified"`, defaulting to `"self_rated"` the
  first time `skill_level` is set (`PlayerService.update_profile`).
- UI badges distinguish the two: `level_source_card_self_rated` (✅) vs.
  `level_source_card_coach_verified` (🏆) in partner/profile cards.
- `docs/VISION.md` lists "Coach Verified Level" and "Verified Coaches"
  under Pillar 2 (Trusted Community) as future ideas, not shipped scope.

What does **not** exist yet: there is no `Coach` role, no coach-facing
verification flow, no permission system distinguishing a coach from a
regular player. `level_source` is currently set by the player themselves
(self-reported), not by any actual coach-verification mechanism — the
field is forward-compatible plumbing, not the feature.

As with "On Court Now," this section should be expanded from the actual
approving conversation once the Coach Role's specifics (who can grant
`coach_verified`, how a coach identity is established, any new
model/table) are decided — do not treat the `level_source` field as
evidence the full feature is built.

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
- New flow (onboarding and Edit Profile): **Select Tennis Zone → that
  zone's courts (+ any Custom Courts already selected) → ➕ Add my own
  court**. Find Partner's Smart Filter reuses the same zone-scoped court
  picker, scoped to whichever zone the filter is currently searching. See
  "Custom Courts" below for the add-your-own-court decision in detail.

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

**Why:** this is where UX regressions get caught cheaply. Sprint 10.3
Phase 2 shipped a working, tested Court Registry; product review then
caught two things pure functional testing wouldn't: the Edit Profile
Courts flow needed to be confirmed as always showing the zone picker
(never silently defaulting to the home zone), and the custom-court flow
only confirmed via text instead of showing the court checked immediately.
Both were fixed in the same sprint, before commit, because they were
raised as review questions rather than accepted as shipped behavior — see
"Custom Courts" above for the resulting design.

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
