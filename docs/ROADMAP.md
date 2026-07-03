# Baseline Product Roadmap

Version: 1.2

**Purpose:** the phase-level summary of what's still ahead. If a phase or
item is listed here, it has not shipped yet. For the epic-level
breakdown of this same forward plan (Goal/MVP/Phase 1/Phase 2/Future per
epic) — the single planning document for future development — see
`docs/BACKLOG.md`.

**What belongs here:** future phases and the features planned for them,
at roadmap granularity (not sprint-level task breakdowns).

**What must never be duplicated here:** anything already shipped (→
`RELEASE_NOTES.md`), epic-level MVP/Phase breakdown (→ `docs/BACKLOG.md`),
the reasoning behind a specific decision (→ `docs/PRODUCT_DECISIONS.md`),
or long-term vision/principles (→ `docs/VISION.md`, `PRODUCT.md`).

---

## Vision

A simple platform that helps tennis players find partners, organize matches, participate in tournaments and build their playing history.

---

## Phase 2 — Community

Status: In progress — Browse Open Matches, Join Match, Better search
filters, and Favourite courts have shipped (see `RELEASE_NOTES.md`,
Sprint 7.0 and Sprint 10.3). Remaining:

- Public Match Feed
- Nearby matches

---

## Phase 3 — Competition

Status: Planned

- Tournaments
- Round Robin
- Knockout
- Match Results
- Score Entry
- Standings

---

## Phase 4 — Player Growth

Status: Planned

- Match History
- Player Statistics
- Coach Verification
- Achievements

---

## Phase 5 — Social

Status: Future

- Friends
- Favourite Players
- Player Reviews
- Rematch
- Chat
- Notifications

---

## Phase 6 — Mobile App

Status: Future

- iOS
- Android
- Push Notifications
- Maps
- Calendar Sync

---

## Engineering Principles

- Build MVP first.
- Keep architecture simple.
- Reuse existing services.
- No duplicated business logic.
- Every feature requires:
  - Tests
  - Telegram E2E verification
  - Documentation update

---

## Long-Term Vision

"Baseline should become the easiest way for tennis players to find games, improve their level and build a local tennis community."
