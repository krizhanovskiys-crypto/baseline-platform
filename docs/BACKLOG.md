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

- **MVP:** Permission levels — today `/dev` is a single flat allowlist
  with no distinction between Moderator, Admin, and Owner.
- **Phase 1:** Real user management (view/edit/suspend a real player),
  match moderation (force-cancel, inspect any match).
- **Phase 2:** Report Abuse admin review queue (see Epic 7 for the
  player-facing half), analytics visibility in `/dev` (the analytics
  pipeline already collects events — nothing surfaces them yet),
  environment visibility in `/dev` (confirm which `ENV`/config is active).
- **Future:** —

---

## Epic 2 — Tournaments & Competition

**Goal:** support structured competition, not just one-off matches
(`docs/ROADMAP.md` Phase 3, `docs/VISION.md` Pillar 6).

- **MVP:** Tournament model + registration flow — a player commits to a
  tournament, not a single game; this is the prerequisite everything else
  in this Epic depends on.
- **Phase 1:** Round Robin format, Score Entry, Standings (Round Robin is
  the simpler bracket type — the natural first format to support).
- **Phase 2:** Knockout format.
- **Future:** Club Events, League Seasons.

---

## Epic 3 — Coach Platform

**Goal:** support Coach as a first-class user type (`MANIFESTO.md`), not
a self-reported profile label.

- **MVP:** Coach role/identity, distinct from Player.
- **Phase 1:** Coach verification workflow — replaces today's self-set
  `level_source="coach_verified"` flag, which nothing actually verifies.
- **Phase 2:** Coach discovery, coach-specific profile fields.
- **Future:** Lesson organization & scheduling, player recommendation
  from a coach.

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
