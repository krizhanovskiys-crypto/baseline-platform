# Product Backlog

**Purpose:** the single planning document for future development —
every not-yet-built Epic, broken into Goal / MVP / Phase 1 / Phase 2 /
Future so a piece of work can be picked up at the right size.

**What belongs here:** product-facing future work, organized by Epic.
Every item traces back to the approved Product Gap Review (2026-07-02).
Nothing here is invented — this is that review reorganized, not extended.

**What must never be duplicated here:** engineering/technical debt (→
`docs/TECH_DEBT.md` — a race condition, a stale background job, or a
missing DB index is debt, not a product Epic, even if a Gap Review
finding mentioned it), phase-level status narrative (→ `docs/ROADMAP.md`,
which stays the high-level phase summary; this file is the epic-level
breakdown of the same forward plan), ideas not yet promoted onto any
plan (→ `docs/IDEAS.md`), or an accepted, shipped decision (→
`docs/PRODUCT_DECISIONS.md`).

**Explicitly excluded, with reason** (so nothing looks silently dropped):
- **Rating / ELO** — not future work, a product non-goal (`PRODUCT.md`).
- **Scheduled expiry job for Available Now**, **PostgreSQL read-check-write
  race condition** — engineering debt already tracked as TECH-008 and
  TECH-006 in `docs/TECH_DEBT.md`.
- **Blocked-user handling for invitations** — already tracked as TECH-003
  in `docs/TECH_DEBT.md`, with a solution already designed there.
- **"On Court Now"** — raised during Sprint 10 planning but explicitly
  undecided (build it, fold it into Available Now, or drop it); it needs
  a product decision before it can be a backlog item, not a backlog slot
  pre-judging that decision.
- Small, single-shot UX findings from the Gap Review's "Forgotten
  improvements" section that don't decompose into MVP/Phase tiers are
  grouped under Epic 11 below instead of being forced into their own
  Epic.

---

## Epic 1 — Admin Center

**Goal:** give an operator real tools to run the platform as it grows,
beyond direct database access (`MANIFESTO.md`'s Permissions: User,
Moderator, Admin, Owner).

- **MVP — shipped (Sprint 11 Phase 2.1):** Permission levels —
  `OperatorRole` (Moderator/Admin/Owner), `PermissionService` +
  `AdminSessionService` as two deliberately separate authorization/
  authentication responsibilities.
- **Phase 1 — partially shipped:** Admin Center Players module (Sprint
  11 Phase 3.0) covers view (Search/Browse/Details) and one Action
  (grant/revoke the Verified Coach badge). Generic edit and suspend a
  real player, and match moderation (force-cancel, inspect any match),
  are not built.
- **Phase 2 — partially shipped:** environment visibility in `/dev` —
  the Admin Dashboard (Sprint 11 Phase 2.2) already shows live
  Environment/Version/Uptime/stats. Report Abuse admin review queue
  (see Epic 7 for the player-facing half) and analytics visibility in
  `/dev` (the analytics pipeline already collects events — nothing
  surfaces them yet) are not built.
- **Future:** —

---

## Epic 2 — Tournaments & Competition

**Goal:** support structured competition, not just one-off matches
(`docs/ROADMAP.md` Phase 3, `docs/VISION.md` Pillar 6).

- **MVP — shipped (Sprint 12, 12.2):** Tournament model + registration
  flow. Tournament creation/management permission is Admin **or**
  Verified Coach, via one extensible gate
  (`TournamentService.can_create_tournament()`/`can_manage_tournament()`)
  — not hardcoded per-role, exactly as planned, so a future dedicated
  Tournament Organizer permission (below) still only means editing this
  gate's own body. Reached from the Main Menu's role-aware 🏆
  Tournaments button (Sprint 12.2), not `/dev`.
- **Phase 1 — in progress (Sprint 14 "Tournament Engine"):**
  Domain/Persistence/Service Layer shipped — single-day bracket
  progression, Coach/Admin (the Tournament Organizer) enters match
  results, the bracket automatically advances the winner, the
  tournament completes with a determined champion and final standings
  (`docs/ai/history/Sprint-14.md`). Organizer-controlled result entry,
  not player-submitted scores — see `docs/PRODUCT_DECISIONS.md`'s
  "Single-day tournaments use organizer-controlled result entry" and
  `docs/PD-001-Tournament-Result-Reporting.md`. Not yet reachable from
  any client — API Layer and Telegram integration are next
  (`docs/ai/ACTIVE_SPRINT.md`). This supersedes the original
  Round-Robin-first ordering below: bracket/knockout mechanics are now
  the agreed next phase, ahead of Round Robin.
- **Phase 2:** Round Robin format, Score Entry, Standings — deferred
  behind Phase 1's bracket engine, not dropped.
- **Future:** Club Events, League Seasons, a dedicated Tournament
  Organizer permission (today this capability is covered by Admin/Coach;
  a first-class permission of its own is deferred until a real need for
  organizers who are neither shows up). **Player Details from Tournament**
  — tapping a registered player in Registered Players (or Add Player's
  search results) opens their full Player Card (the Universal Player
  Card, Sprint 12.3), not just a name-only row. *Not from the original
  Gap Review* — surfaced during Sprint 12.3's own audit, which found
  Tournament's rosters render names only, with nowhere to tap through to
  a full card; recorded here rather than silently blended in as if it
  always traced back to the 2026-07-02 review.

---

## Epic 3 — Coach Platform

**Goal:** support Coach as a first-class user type (`MANIFESTO.md`), not
a self-reported profile label.

- **MVP — shipped (Sprint 12, 12.2, 12.3):** Coach as a Player Badge
  (`Player.is_verified_coach`) — not a separate entity/model/service,
  superseding this Epic's earlier "distinct from Player" framing. The
  badge is a checkable permission source for Epic 2's Tournament
  creation, reached without any dependency on `/dev` (Sprint 12.2), and
  displayed consistently everywhere a player card appears — My
  Profile, Find Partner, Available Now, Admin Player Details — via the
  Universal Player Card presenter (Sprint 12.3), not a one-off flag
  shown on a single screen.
- **Phase 1:** Coach verification workflow — replaces today's self-set
  `level_source="coach_verified"` flag, which nothing actually
  verifies. Not started.
- **Phase 2:** Coach discovery, coach-specific profile fields.
- **Future:** Lesson organization & scheduling, player recommendation
  from a coach. If Coach ever needs its own lifecycle/credentials beyond
  a badge, revisit the separate-entity option then — not speculatively
  now.

---

## Epic 4 — Match Discovery & Community

**Goal:** help a player find more games than the ones inside their own
Tennis Zone and their own initiative to browse.

- **MVP:** Public Match Feed — a view of open matches distinct from the
  current in-bot, profile-gated Available Matches browsing.
- **Phase 1:** Nearby / geolocation-based matching.
- **Phase 2:** —
- **Future:** —

---

## Epic 5 — Multi-Client Platform

**Goal:** Telegram is only the first client — one backend, multiple
clients (`MANIFESTO.md`).

- **MVP:** REST API parity with the bot — auth, plus the missing
  Invitations / Confirm / Cancel / Leave / Available Now / Court Registry
  endpoints. No real second client can be built on the API as it stands
  today.
- **Phase 1:** Web client.
- **Phase 2:** iOS / Android native apps.
- **Future:** Maps, Calendar Sync, Court availability integration, native
  push notification delivery.

---

## Epic 6 — Player Growth & History

**Goal:** give players a sense of progress and a record of their tennis
life — without ratings or rankings.

- **MVP:** Match History — a player can see a match after it happened,
  not only while it's upcoming.
- **Phase 1:** Player Statistics.
- **Phase 2:** Achievements.
- **Future:** Tennis Passport, Courts Collection, Tennis DNA.

---

## Epic 7 — Trust & Reliability

**Goal:** build a trusted community through verified/earned signals, per
`MANIFESTO.md`'s Trust principle — never through a rating.

- **MVP:** Report Abuse — the player-facing action (the admin-side review
  queue is Epic 1).
- **Phase 1:** Reliability Score, Level Confidence.
- **Phase 2:** —
- **Future:** —

---

## Epic 8 — Social & Friends

**Goal:** players shouldn't lose contact after a great match
(`docs/VISION.md` Pillar 4).

- **MVP:** QR Friend — scan-to-connect after a match, no usernames or
  searching.
- **Phase 1:** Favourite Partners / Add Friend, Play Again (Rematch).
- **Phase 2:** Player Reviews.
- **Future:** Chat, Private Groups.

---

## Epic 9 — Proactive Notifications

**Goal:** reach a player at the right moment, not only in reaction to
something they just did — every notification today is reactive.

- **MVP:** Match reminders ahead of a scheduled match.
- **Phase 1:** Available Now expiry notice.
- **Phase 2:** —
- **Future:** Native push notifications (depends on Epic 5's mobile
  clients existing).

---

## Epic 10 — Geographic Expansion

**Goal:** scale city by city without a code change per city
(`PRODUCT.md`'s Vision: Toronto → Canada → Ukraine → global).

- **MVP:** City-scoped Court Registry — a mechanism to select which
  city's zones/courts apply, instead of the single hardcoded Toronto
  registry in `backend/app/data/courts.py`.
- **Phase 1:** Second city launch, validating the mechanism.
- **Phase 2:** Additional cities.
- **Future:** Country-level expansion tooling.

---

## Epic 11 — UX Polish Backlog

**Goal:** smaller UX findings from product review that were explicitly
scoped out of a sprint and never revisited. Listed flat per tier — these
are single-screen fixes, not staged builds.

- **MVP:** —
- **Phase 1:** Merge the read-only Profile screen into Edit Profile (no
  content on the former that isn't already on the latter).
- **Phase 2:** —
- **Future:** "+N more" courts indicator on Find Partner cards; weekday
  label for custom Organize Match dates; a direct "Organize a match"
  shortcut on the My Matches empty state; removing the redundant
  match-type/player-count line on Organize Match's Confirm/Success
  screens; Main Menu button reorder; Edit Profile field reorder.

---

## Related documents

| Document | Relationship |
|---|---|
| `docs/ROADMAP.md` | Phase-level summary of the same forward plan |
| `docs/PRODUCT_DECISIONS.md` | Where an Epic's design lands once it ships |
| `docs/TECH_DEBT.md` | Engineering debt — a different kind of "not done yet" |
| `docs/IDEAS.md` | Ideas not yet promoted onto this backlog |
