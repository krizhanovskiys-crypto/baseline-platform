# Active Sprint

**Purpose:** the current sprint's checklist only — nothing else. When a
sprint ends, its content moves into `docs/ai/AI_HANDOFF.md` as a dated
entry, `RELEASE_NOTES.md` gets the shipped-feature summary, and this
file is reset for the next sprint.

---

## Current Sprint

Sprint 14 — Tournament Engine (Phase 1). Plan:
`docs/Sprint14_Tournament_Engine_Plan.md`. Commits `58d4e8a` and
`8c15af3`, both pushed. Detail: `docs/ai/history/Sprint-14.md`.

## Completed — Domain / Persistence / Service Layer

- `Game.round`, `Game.winner_player_id` (migration `e417d3f7d1a4`),
  applied to the real dev database.
- `MatchLifecycleService`: `OPEN → IN_PROGRESS` for tournament matches
  only (context-aware exception, not a blanket transition change).
- `TournamentService`: `generate_matches()` now requires a
  power-of-two player count; new `start_match()`, `complete_match()`
  (PD-001 — organizer-only, Winner-only, no score), next-round
  generation, `get_standings()` (computed, not stored).
- Create Tournament's `max_players` input validates power-of-two at
  entry time, not just later at Generate Matches.
- `docs/PRODUCT_DECISIONS.md`, `docs/PD-001-Tournament-Result-Reporting.md`
  reconciled — no contradictions found.

## In Progress

Nothing currently in progress.

## Blocked

Nothing currently blocked.

## Next

**API Layer** (`docs/Sprint14_Tournament_Engine_Plan.md` Step 2) —
design and implement `/api/v1/tournaments` endpoints (create, list,
detail, entries, standings) and `PATCH /games/{id}/result`, per
`docs/Baseline_API_v2_Architecture.md` §9. Authorization for each
endpoint checked explicitly against Domain Model §3/§4 and PD-001, not
inherited implicitly.

**After that:** Telegram integration (Step 4) — bot flow for
Coach/Admin to create a tournament, browse/join for any player, and
report a result, reusing `TournamentService` from the client-agnostic
service layer already built. iOS integration (Step 5) can start in
parallel once the API is real.

Not started — no implementation tasks broken out yet.
