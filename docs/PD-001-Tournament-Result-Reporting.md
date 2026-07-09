# Product Decision 001 — Tournament Result Reporting

**Type:** Product Decision (see `DECISION_PROCESS.md`) — does not touch Domain Model or API shape, only who's authorized to call the already-planned `PATCH /games/{id}/result` and what triggers after.

---

## Decision

**The Tournament Organizer reports the result. Not the players. Not automatic. Not two-sided confirmation.**

Organizer = Verified Coach or Admin (future: Club Organizer) — the same actor who created the Tournament, per `Baseline_Domain_Model.md` §4.

## Why

Baseline's tournaments are one-day, high-volume, fast-turnaround — round after round, same afternoon. The organizer is physically at the courts. They see the result. They enter it. A two-sided player-confirmation flow adds a wait state Baseline's format can't afford, and this is a live-event tool, not an asynchronous ladder app.

## Scope, deliberately narrow

**In Sprint 14:** `Winner` only. A single field, one Player ID, nothing else.

**Explicitly not in Sprint 14 (Sprint 18+ per current estimate):** score detail (`6:4 6:2`, `7:6 6:7 10:8`), sets, duration — any of it. Adding score now would turn a one-field product rule into a data-modeling question again, and this decision is about *who*, not *what*.

## The pipeline this triggers

```
Organizer enters Winner
        ↓
Game closes (status → completed)
        ↓
Standings recompute (that tournament only, per the locked "no accumulation" decision)
        ↓
Next round's Game gets created, if the bracket/ladder logic says one should
        ↓
Notification sent
```

**Note on the last step:** `Notification` as a delivered feature is still future work — `Baseline_Domain_Model.md` §8 marks it `(future)`, and `Sprint14_Tournament_Engine_Plan.md`'s exclusion list says Notifications aren't built this sprint. Resolving that tension: Sprint 14 implements the pipeline through Standings and next-Game creation for real; the Notification step is a logged/stubbed call for now — the seam exists, the actual push/delivery mechanism doesn't ship until Notification's own sprint. Not a scope violation, just naming the boundary precisely instead of leaving it implied.

## What this decision does NOT touch

No change to `Baseline_Domain_Model.md` or `Baseline_API_v2_Architecture.md` — Tournament, Game, and Standings are exactly as those documents already describe. This PD only answers "who's allowed to call the result endpoint, and what happens next," which is service-layer/product behavior, not foundation.

---

## Future Impact

This decision affects:

✓ Backend
✓ Telegram
✓ iOS

Deferred:

• Notifications
• Web Admin
