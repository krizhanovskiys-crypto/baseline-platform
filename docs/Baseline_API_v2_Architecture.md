# Baseline API v2 — Architecture

> No code in this document. This is the blueprint the Python backend work gets built from, the same way `BaselineDemo_v4.md` was the blueprint for the iOS UI. Source of the gaps this document addresses: `BACKEND_GAPS.md`, found during iOS Sprint 1.

---

## 1. Why v2, not just "add endpoints to v1"

v1 (`/api/v1/players`, `/api/v1/games`) was designed around one client: the Telegram bot, where the bot's own session state covers things the API never had to expose (who's currently online, in-memory match flow state, etc). Now that iOS is a second, independent client with no shared session, several of those implicit behaviors need to become explicit, stateless API contracts.

That's a different job than "add a missing field." It's why this is a v2 architecture pass, not five unrelated tickets.

**Decision (locked):** stay on `/api/v1`, no `/api/v2` prefix. Pre-production, with no external clients to protect, a second prefix would be versioning theater — additive-only evolution of v1 achieves the same safety with less to maintain. The "v2" in this document's title refers to this second architecture *pass*, not a URL version.

---

## 2. Design principles for this API

Borrowing the spirit of `Baseline_Design_Principles.md`, translated to backend terms:

- **Additive, not disruptive** — nothing in this pass changes an existing endpoint's contract; the bot must keep working without a single line of bot code changing.
- **Stateless** — the bot currently gets away with in-memory wizard state; the API can't. Every new endpoint must be callable cold, with no assumed prior request.
- **One source of truth** — "available now," "open matches," "standings" must be computed from the database, never duplicated logic between bot and API.
- **Non-goals stay non-goals** — `PRODUCT.md` rules out ELO/rating systems. Every new domain below gets checked against that explicitly (see §7).
- **API First** — any new feature is designed as an API contract before any client touches it. Telegram, iOS, and (eventually) Web all consume the same contract; no client gets feature logic the others don't, and no client computes something the server should own.

---

## 3. Current state (v1) — confirmed, unchanged

```
GET    /health
GET    /api/v1/players/
POST   /api/v1/players/
GET    /api/v1/players/{id}
PATCH  /api/v1/players/{telegram_id}
GET    /api/v1/players/{telegram_id}/partners
GET    /api/v1/games/                  (optional ?area=)
POST   /api/v1/games/
GET    /api/v1/games/{id}
```

These are not touched by this document. Everything below is additive.

---

## 4. New domain: Authentication

**Why it's first:** every other domain below assumes "the current player," and right now that's a bare, unverified `telegram_id` passed by whichever client feels like it. That's fine for a bot living inside Telegram's own auth, but not for a standalone iOS client.

**Proposed shape (endpoints, not implementation):**
- A token-issuing endpoint that accepts *something Telegram already gives us* (Telegram's own Login Widget / WebApp `initData` signature) and returns a session token tied to a `telegram_id`. This reuses Telegram as the identity provider rather than building a parallel identity system — smallest lift, and consistent with the bot being the "first client."
- All other new endpoints below assume a token, not a bare `telegram_id`, once this lands.

**Decision (locked):** Telegram-only identity. No Sign in with Apple, not now, not on this roadmap. Baseline's whole user base already has Telegram — a second identity system would add complexity for a population that doesn't exist yet. Revisit only if a real product reason for non-Telegram users appears.

---

## 5. New domain: Availability

**Backs:** the bot's existing "🔥 I'm Available" feature, and iOS Home's "Available Now" rail + toggle.

**What's missing:** the bot presumably tracks this in memory or a lightweight table already (2-hour expiry, per the feature description) — but it's not exposed. Two proposed endpoints:
- Mark self available (with the existing 2-hour expiry behavior)
- List currently-available players, filterable by zone — likely a variant of the existing partners/list logic with an availability filter, not a wholly new query shape

**Decision (locked):** a field on Player (`available_now`, `available_until`), not a separate resource. One player, one changing state — a second resource would be a second source of truth for something that's fundamentally an attribute of Player. The existing `/players/{telegram_id}/partners` endpoint gains an `?available_only=true` filter instead of a parallel endpoint tree.

---

## 6. New domain: Match lifecycle mutations

**Backs:** bot's join / leave / cancel / add-player actions (confirmed in the bot feature table), and iOS Play's "Join" button, My Matches actions, Match Details actions.

**Missing mutations on the existing Game resource:**
- Join a game (as a player)
- Leave a game
- Cancel a game (organizer only)
- Add a specific player to a game (organizer-initiated invite — matches the iOS "Invite to Match" flow from Player Profile)

**Decision (locked):** 100% server-side. No business logic on any client. Telegram and iOS must get identical responses from the backend for identical actions — a client-side validation copy would drift the moment one client's logic gets updated and the other doesn't.

---

## 7. New domain: Statistics

**Backs:** iOS Profile's Statistics tab (matches played, win rate, streak, favorite court, most frequent partner, monthly activity).

**Non-goals check:** `PRODUCT.md` rules out ELO/rating. Win rate and streak are **derived from match history, not a persistent skill rating** — a player's win rate isn't used to rank or match them against anyone, it's a personal mirror, same category as Strava showing your pace without implying a leaderboard. This document's position: stats as described do **not** conflict with the non-goal. Flagging explicitly so it's a conscious call, not an accidental scope creep past `PRODUCT.md`.

**Decision (locked):** dedicated endpoint, `GET /players/me/stats`. No client — iOS included — computes win rate or streak locally. That logic lives in exactly one place.

---

## 8. New domain: Achievements

**Backs:** iOS Profile's Achievements tab.

**Bigger decision than an endpoint:** nothing today tracks badge-worthy events at all. This needs, in order:
1. A decision on the actual badge list (product decision, not engineering — "First Match," "10 Matches," "Early Bird," etc. were placeholders in the iOS mockup, not a real spec)
2. A rule engine or simple triggers (e.g. "on game completion, check streak/count thresholds") — could be computed on-demand from stats (§7) rather than stored, if the badge list stays simple
3. An endpoint returning unlocked + locked badges for a player

**Recommendation:** don't build a generic "rules engine" — start with badges computed live from the stats endpoint's data (no new storage), and only add a dedicated achievements table if the badge list grows complex enough to need history ("first unlocked on...").

---

## 9. New domain: Tournaments

**Backs:** iOS Tournaments tab entirely (Live Now, Upcoming, My Tournaments, standings, Tournament Details, matchups).

**This is the largest new domain, and the one most likely to need a real product conversation before any backend design, for one specific reason:**

**Decision (locked): Tournament Standings, not "points."** The word itself is retired from this domain — "points" implies something that accumulates and carries meaning, which is exactly the shape `PRODUCT.md`'s non-goal rules out. Standings exist **only inside their own tournament**. Once a tournament ends, its standings remain readable as history *of that tournament* — nothing propagates to the player, nothing accumulates across tournaments, no global leaderboard, no ELO, no rating-by-another-name.

Rough shape, consistent with that decision:
- Tournament resource (name, format, level range, zone, dates, status: upcoming/live/completed)
- Entry resource (player ↔ tournament, join/leave)
- Standings, scoped to one tournament, computed from that tournament's completed matches only, archived with the tournament once it ends
- A tie/matchup concept connecting a tournament round to a Game (reuses the existing Game resource rather than inventing a parallel "tournament match" type — a tournament tie is a Game with a tournament_id and round attached to it)

---

## 10. Sequencing recommendation

Matches the iOS integration order already in motion (Home next, then Play, then Tournaments):

1. **Auth** (§4) — blocks real testing of everything else beyond one hardcoded dev player
2. **Availability** (§5) — unblocks Home
3. **Match lifecycle mutations** (§6) — unblocks Play
4. **Statistics** (§7) — unblocks Profile's remaining tabs (already partially wired)
5. **Achievements** (§8) — small, depends on §7
6. **Tournaments** (§9) — largest, and has an open product question that should be resolved first, so it's last on purpose, not just by size

---

## 11. Decisions log — all resolved

| # | Question | Decision |
|---|---|---|
| 1 | `/api/v2` prefix vs. evolve v1? | **Stay on `/api/v1`**, additive-only |
| 2 | Telegram-only vs. Sign in with Apple? | **Telegram-only**, permanent for now |
| 3 | Availability as Player field vs. own resource? | **Player field** (`available_now`, `available_until`) |
| 4 | Server-side join validation? | **100% server**, no client business logic |
| 5 | Stats: pre-aggregated vs. raw history? | **Dedicated endpoint**, `GET /players/me/stats` |
| 6 | Tournament points vs. per-tournament standings? | **Standings only** — no word "points," no cross-tournament accumulation, no rating |

Nothing above is still open. This document is now a locked reference, same status as `BaselineDemo_v4.md` on the UX side.

---

*This document is resolved and locked. Next: `Baseline_Domain_Model.md` — the entity-relationship blueprint (Player, Game, Tournament, Club, Coach, Achievement, Notification) that this API contract will eventually express. Only after that does Python backend work begin, per the "API First" principle in §2.*
