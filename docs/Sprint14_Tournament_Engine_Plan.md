# Sprint 14 — Tournament Engine (Phase 1)

> Execution plan. References `Baseline_Domain_Model.md`, `Baseline_API_v2_Architecture.md`, and `PD-001-Tournament-Result-Reporting.md` as locked inputs — nothing here re-opens those. Scope is explicitly **Phase 1**: Verified Coach / Admin creation path only (per Domain Model §4) — no Club, no Club Organizer path (future, not this sprint).

---

## Step 0 — PD-001: Tournament Result Reporting

Read and confirmed before any implementation: `PD-001-Tournament-Result-Reporting.md`. Locks who reports a result (Tournament Organizer — Verified Coach or Admin, never players, never automatic) and the Winner-only scope (no score until Sprint 18+). Step 1 below depends on this being settled first, since it determines the Game fields needed.

---

## Step 1 — Domain model implementation

**Deliverables (backend/app/models/ or wherever Player/Game live today):**
- `Tournament`: name, format, level_range, zone, dates, status (upcoming/live/completed)
- `TournamentEntry`: player ↔ tournament join table, join/leave timestamps
- `Game` gains: `tournament_id` (nullable FK), `round` (nullable int), `status` (upcoming/completed/cancelled), `winner_telegram_id` (nullable — set only by the Tournament Organizer, per PD-001; no score field, per PD-001's explicit Sprint 18+ deferral)
- `Player` gains: `is_verified_coach` (bool), `is_admin` (bool) — per Domain Model §7/§7.1. Note: `is_admin` should probably migrate the existing `DEVELOPER_IDS` env-list into a real column, not add a second parallel admin concept — flag this to Claude Code as a judgment call to make against the real code, not decided here.
- Standings: **not a table.** Computed from completed Games where `tournament_id` matches, scoped to that tournament only, per the locked "no accumulation" decision.

**Migration:** one Alembic migration covering all of the above together (Tournament, TournamentEntry, Game's new columns, Player's new columns) — they're one coherent change, not four.

**Tests for this step:** repository-level tests only (per existing convention — real in-memory SQLite, no mocks) confirming the new tables/columns exist and basic CRUD works. Service-level and API-level tests come in Step 6.

---

## Step 2 — API design for Tournament Engine

Design as a spec (docstrings / OpenAPI, whatever the existing FastAPI convention is) before writing route bodies. Endpoints, all under `/api/v1` (per the locked "no v2 prefix" decision):

```
POST   /tournaments/                        Create (Verified Coach or Admin only)
GET    /tournaments/                        List (filterable by zone, status)
GET    /tournaments/{id}                    Detail
POST   /tournaments/{id}/entries            Join (any eligible Player)
DELETE /tournaments/{id}/entries/{player_id}  Leave
GET    /tournaments/{id}/standings          Computed, read-only
POST   /tournaments/{id}/games              Schedule a tie (creates a Game with tournament_id+round)
PATCH  /games/{id}/result                   Report winner (organizer only — per ADR-001)
```

**Authorization matters more than shape here** — every write endpoint needs its permission rule checked against Domain Model §3/§4 and PD-001 explicitly:
- Tournament create: Verified Coach or Admin (Domain Model §4)
- Entry create/delete: the Player themself only
- Game result (`PATCH /games/{id}/result`): the Tournament Organizer only — Verified Coach or Admin, **never the players**, per PD-001. For a tournament tie, "organizer" means whoever created that Tournament, not whichever player happened to create a standalone Game — this needs to be explicit in the permission check, not inherited from Game's normal organizer rule.

---

## Step 3 — Backend implementation

Follow the existing layering exactly (`Handlers → Services → Repositories → Database`, per `docs/ARCHITECTURE.md` — this sprint doesn't get an exception). Concretely:
- `TournamentService` — transport-agnostic, holds all the rules from Step 2's authorization list
- `TournamentRepository` — the only thing touching the DB for Tournament/TournamentEntry
- API handlers stay thin — call the service, render the response, nothing else (same rule the bot already follows)

**This step should NOT touch bot or iOS code.** Backend-only, so it can be fully tested (Step 6, backend slice) before either client integrates.

---

## Step 4 — Telegram integration

New bot flow, additive to the existing menu (per `docs/ARCHITECTURE.md`'s conventions for adding a feature):
- Coach/Admin: a way to create a Tournament (likely a wizard, matching the existing Organize Match pattern)
- Any player: browse Tournaments in their zone, join/leave
- Organizer of a scheduled tie: report result

Reuses `TournamentService` from Step 3 — the bot's handlers call the same service the API does, per API First / one-source-of-truth.

---

## Step 5 — iOS integration

This is where the existing work connects:
- `TournamentDTO`, `TournamentEntryDTO`, `StandingsDTO` — new files in the `Networking/` group already established in `BaselineDesignSystem`
- `TournamentService.swift` (iOS-side, naming collision with backend's is fine, different layer) wrapping the new endpoints
- `TournamentsMockData.swift` gets **deleted**, not kept alongside — `TournamentsView.swift` and `TournamentDetailsView` switch to a `TournamentsViewModel` the same shape as the existing `ProfileViewModel` (loading/error/loaded states, per the pattern already in the codebase)
- No new screens, no new components — per your original Sprint iOS rule, still in effect: this is a data-source swap on already-built UI

---

## Step 6 — Test coverage

Per existing convention (`pytest`, real in-memory SQLite, one file per feature):
- `tests/test_tournaments.py` — repository + service layer, covering every authorization rule from Step 2 explicitly (Verified Coach can create, plain Player cannot, non-organizer cannot report a result, etc.) — these permission tests matter more than happy-path tests here
- API-level tests hitting the actual endpoints, confirming status codes match the authorization rules (403 where expected, not just 200 where expected)
- iOS: no new UI tests needed (no new UI) — but the DTO decoding against a real API response is worth one test, same pattern as any other DTO

---

## Step 7 — Demo

Script, not slides — walk through, in order:
1. Admin verifies a Coach (or Admin creates directly)
2. Coach creates a Tournament in a zone
3. Two seeded test players join via the bot
4. A tie gets scheduled (Game with tournament_id)
5. Organizer reports a result via the bot
6. Open the iOS app, Tournaments tab — Live/Upcoming/Standings all real, no MockData
7. Confirm the same Tournament, same Standings, visible from both clients — this is the actual point of the whole platform framing, worth saying out loud in the demo, not just showing

---

## What's explicitly NOT this sprint

- Club / Club Organizer path (Domain Model §4's future half)
- Score/sets detail beyond win/loss (ADR-001 scoped this out on purpose)
- Dispute resolution for contested results
- Achievements reacting to Tournament results (Domain Model §6 — separate, later)
- Notifications for tournament events (Domain Model §8 — the pipeline *seam* exists per PD-001, actual delivery mechanism is separate, later work)

If any of these come up mid-sprint, per your rule: backlog, or a new ADR if it's genuinely blocking — not a redesign of this plan.
