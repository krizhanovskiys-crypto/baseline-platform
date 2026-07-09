# Baseline Domain Model

> Not API. Not SQL. Not Python. This is the model of the *business*, not the system — who exists, who owns what, who is allowed to change what, and how entities relate to each other. `Baseline_API_v2_Architecture.md` describes the contract clients talk to; this document describes what that contract is a contract *about*. Per the API First principle, this should be stable underneath the API, not the other way around.

---

## 0. How to read this document

Every entity below is described in four parts, in this order:

```
What it is    →  the real-world thing this represents
Created by    →  who/what brings it into existence
Owned by      →  who has the authority to change or delete it
Relates to    →  its connections to other entities in this model
```

Entities marked **(future)** don't exist in the system today — they're modeled now because you named them as coming soon (Clubs, Web Admin, Tournament Engine), and getting their shape roughly right early is cheaper than retrofitting Player/Game once Clubs exist and start pulling on them.

---

## 0.1 Platform framing

As of this document, Baseline stops being described as "a Telegram bot with an iOS app." It's one platform with multiple clients, all built on the same backend and the same domain model below:

```
Baseline Platform
├── Backend        (the one source of truth — everything in this document lives here)
├── Telegram       (first client, ships today)
├── iOS            (second client, in progress)
├── Web Admin      (future client — the natural home for whatever "Admin" turns out to need, §7.1)
└── Android        (future client)
```

This isn't a relabeling exercise — it changes how future decisions get framed. A feature is never "a bot feature" or "an iOS feature" anymore; it's a **platform capability**, exposed through whichever clients need it, per the API First principle already locked in `Baseline_API_v2_Architecture.md`. Every entity below is described client-agnostically for exactly this reason.

---

## 1. Player

**What it is:** a real person using Baseline — the root identity everything else attaches to.

**Created by:** self-registration through Telegram (the only identity provider, per the locked API decision). A Player cannot be created by another Player or by the system on someone's behalf.

**Owned by:** the Player themself, exclusively. No one else can edit another player's name, level, zone, courts, or languages — not an organizer, not a future Club admin, not a Coach.

**Relates to:**
- Has zero or one active **Availability** state (§2) — not a separate entity, an attribute of Player itself
- Organizes zero or more **Games** (§3)
- Participates in zero or more **Games** as a joiner
- Enters zero or more **Tournaments** (§4)
- Has computed, read-only **Statistics** — derived from their Games, never stored as something a Player "owns" and edits
- Has computed, read-only **Achievement** unlocks (§6)
- **(future)** Belongs to zero or more **Clubs** as a member
- **(future)** May *also* be a **Coach** — not a separate person, a capability a Player can hold (see §7)
- **(future)** Receives **Notifications** (§8) — always the recipient, never the creator

---

## 2. Availability

**What it is:** a temporary, self-declared state — "I'm free to play right now."

**Created by:** the Player themself, and only for themself.

**Owned by:** not an independently owned entity — it's a state that lives on Player (per the locked API decision: `available_now`, `available_until`). Modeled here separately anyway because it has its own lifecycle rule worth naming: it **expires on its own** (time-based, ~2 hours), which no other Player attribute does. No one — not the Player, not an admin — needs to manually turn it off; it's the one piece of Player state with a built-in clock.

**Relates to:** exists only in relation to its one Player. Never referenced by Games, Tournaments, or anyone else directly — other entities query "which players are available," they don't hold a reference to an Availability record.

---

## 3. Game

**What it is:** a single, concrete tennis match — real date, real time, real court, real (or open) set of players. This is the same entity whether it originated from the bot's "Organize Match" wizard, iOS's Organize Match flow, or (per §4) a tournament round.

**Created by:** a Player, who becomes its **organizer**. A Game can also be created by the system on behalf of a Tournament (a scheduled tie) — see §4 for how that ownership differs.

**Owned by:** the organizer, while the Game is upcoming. Ownership is transferable in exactly one direction: a standalone Game can never become a tournament tie after the fact, and a tournament tie's Game is owned by the Tournament (§4), not by either participating Player, for as long as it's part of that tournament.

**Who can mutate what (this is where join validation from the API doc becomes a domain rule, not just an implementation detail):**
- Organizer: edit details, cancel, add a specific player, remove a player
- Any other Player: join (if open and level-eligible), leave (if joined)
- No one: change the outcome/score after the fact except through whatever future "report result" action gets designed — not modeled yet, flagged as an open gap in §9

**Relates to:**
- Has one organizer **Player**, and a set of participant **Players** (many-to-many — a Player can be in many Games, a Game has many Players)
- Optionally belongs to one **Tournament**, as a specific round's tie — when this is set, the Game's mutation rules above are superseded by Tournament rules (§4), not both at once
- Feeds into the organizer's and every participant's computed **Statistics**

---

## 4. Tournament (future)

**What it is:** a structured competitive event — a ladder, a cup, a round-robin — scoped to a zone and level range, made up of scheduled Games (ties) between entered Players.

**Created by (locked): a Verified Coach or an Admin — not any Player.** This mirrors how the Telegram bot already draws this exact line for its own elevated actions (`/dev`, gated by `DEVELOPER_IDS` — see §7.1). Ownership chain today:

```
Player
  ↓ (verification, granted by Admin — not self-declared)
Verified Coach
  ↓ (creates)
Tournament
```

**Future path, once Club (§5) is real:**

```
Club
  ↓ (holds the role)
Club Organizer
  ↓ (creates, on behalf of the Club)
Tournament
```

Both paths can coexist — a Verified Coach doesn't stop being able to create a Tournament once Clubs exist; a Club Organizer is a second, additive path, not a replacement.

**Owned by:** its creator, whoever that turns out to be — controls entries open/close, can cancel the tournament, cannot alter individual Standings by hand (those are always computed, per the locked decision, never manually entered).

**Relates to:**
- Has many **Entries** — a join entity between Player and Tournament, since a Player joining a Tournament is a distinct fact from a Player joining a single Game (an Entry can exist before a single Game/tie has even been scheduled)
- Has many **Games**, each tagged as a specific round's tie
- Has **Standings** — not a stored entity, a computed view over that Tournament's completed Games, scoped to exist only within this Tournament (per the locked "no points, no accumulation" decision) — Standings have no existence or meaning outside their one Tournament, and are never read by Player or by any other Tournament
- **(future)** May belong to a **Club**, if the "who can create a Tournament" question resolves toward Clubs being the accountable owner

---

## 5. Club (future)

**What it is:** a group — a real tennis club, or an informal community group — that can have members, host Tournaments, and (loosely) associate with Courts.

**Created by:** not modeled yet — this is the least-specified entity in this document, named because you flagged it as coming, not because there's a concrete plan for it yet. Flagged in §9 as needing its own product scoping pass before any real modeling continues.

**Owned by:** presumably one or more admin-role Players, but "roles within a Club" (owner vs. admin vs. member) isn't designed here — noted as a gap, not guessed at.

**Relates to:**
- Has many member **Players**, with some notion of membership role not yet defined
- **(tension worth flagging now, not later):** Courts today are freeform strings a Player types into their own profile (`courts: [String]`) — there's no canonical Court entity. A Club will want to *own* real courts as first-class things (to schedule against, to book, to attach to Tournaments). That's a real modeling conflict between "Court as a string on Player" (today) and "Court as an entity owned by a Club" (future) — resolving it isn't needed today, but whoever designs Club should read this paragraph first, not rediscover the conflict from scratch
- May host **Tournaments** (see §4's open question)
- May employ or host **Coaches** (§7)

---

## 6. Achievement

**What it is:** a recognition of something a Player did — "First Match," "10 Matches Played," etc. Per the locked API decision, these are **computed from Statistics, not independently stored** unless the badge list grows complex enough to need its own history.

**Created by:** the product/system — a fixed, designed list of achievement definitions. No Player and no Club creates an Achievement; they only unlock ones that already exist in that fixed list.

**Owned by:** the system owns the definitions. A Player "owns" their own unlocked/locked status against each definition, but only in the read-only sense of "this is true about me" — a Player cannot manually unlock or hide an achievement.

**Relates to:** derived entirely from a Player's **Statistics**, which are derived entirely from their **Games**. This is a one-way dependency chain (Game → Statistics → Achievement) — nothing flows backward.

---

## 7. Coach (future, partially scoped)

**What it is:** was fully unscoped as of the previous version of this document. As of the Tournament decision (§4), it now has exactly one concrete capability: a **Verified Coach** may create Tournaments. Everything else about what a Coach does on Baseline — paid lessons, group clinics, anything beyond that one capability — is still unscoped, and shouldn't be guessed at here.

**Created by / Owned by:** a Coach is not a separate person-entity — it's a **verification status on a Player**, granted by an Admin (§7.1), not self-declared. A Player requests or is offered verification; they don't grant it to themselves, the same way the bot's `/dev` menu isn't something a Player can turn on for themself.

**Relates to:**
- Attaches to exactly one **Player** — the same "role, not a second identity" pattern as Game's "organizer"
- Once verified, may create **Tournaments** (§4)
- **(future, fully unscoped)** may relate to **Club** — a Coach employed by or hosted at a Club isn't modeled yet

### 7.1 Admin

**What it is:** the other half of Tournament's creation rule, and worth naming explicitly rather than leaving as an implied concept. This isn't a new invention — the Telegram bot already has this exact role today, confirmed in the README: the `/dev` hidden developer menu, gated by `DEVELOPER_IDS`. Admin in this domain model is that same concept, generalized beyond one hardcoded ID list.

**Created by:** not modeled as a self-service flow — realistically a manually-maintained list today (mirroring `DEVELOPER_IDS`), and the natural first real feature for the future **Web Admin** client (§0.1) once it exists.

**Owned by:** itself a trust boundary, not owned by any Player — an Admin *is* a Player with an elevated flag, the same "capability on Player" pattern as Coach.

**Relates to:**
- Can verify a Player as a **Coach**
- Can create **Tournaments** directly (without needing Coach verification first)
- **(future)** Likely the actor behind whatever moderation Club (§5) ends up needing

---

## 8. Notification (future)

**What it is:** a message to a Player, triggered by something another entity did — someone joined your Game, a tournament round was scheduled, an achievement unlocked.

**Created by:** never a client, never directly by another Player. Always the system, reacting to a state change in some other entity (Game gains a participant → Notification to the organizer; Tournament schedules a round → Notification to both players in that tie; Achievement unlocks → Notification to that Player).

**Owned by:** its recipient Player — can mark read, can dismiss. Cannot be created, edited, or sent by any Player to any other Player directly (Baseline has no "send a message" concept in this model — that would be a much bigger feature, chat, not a notification).

**Relates to:** every other entity in this model is a potential *source* of a Notification, but Notification never feeds back into any of them — it's a leaf, not a hub. Good candidate for an event-driven design later (something changes → an event fires → a Notification gets created), but that's an implementation shape, not a domain concern, and stays out of this document on purpose.

---

## 9. Open questions this document surfaces (not resolved here)

Unlike the API document, these aren't yours to rubber-stamp in five minutes — they're real product questions this modeling pass exposed. (Tournament's "who can create one" is no longer on this list — resolved in §4.)

1. **What is a Club, concretely?** Named but not scoped. Needs its own short product pass — even a one-page "what a Club can do" — before real modeling continues.
2. **The Court conflict** (§5): freeform string on Player today vs. a first-class entity a Club would need tomorrow. Not urgent, but real — worth a deliberate decision whenever Club work starts, not an accidental one.
3. **What does a Coach do beyond creating Tournaments?** Narrower than before, but still open — paid lessons, clinics, anything beyond §7's one confirmed capability is unscoped.
4. **How does a Game's result get recorded?** Noticed while writing §3: nothing in this model — or in the API document — covers "someone won." Statistics (win rate, streak) depend on this existing somewhere. This is still the most urgent gap in this whole document — more than Club or Coach — because Statistics (already decided, already has an API endpoint planned) silently depends on it.

---

## 10. Architecture phase — closed

UX Architecture (v4) → Design Principles → Design System (code) → API Architecture → Domain Model. Four documents plus one buildable component library, all cross-referencing each other, none contradicting another. That's the full stack, and per your call, it's done.

Everything from here is engineering against these documents, not producing a sixth one. The four open questions in §9 aren't exceptions to that — they're explicitly-scoped-out product decisions for later, the same way Tournament's creator question was until this message resolved it. Noticing them was the job of this phase; answering them isn't required to start building.

*Baseline Platform: Backend, Telegram, iOS, Web Admin (future), Android (future) — one domain model underneath all of them, starting now.*
