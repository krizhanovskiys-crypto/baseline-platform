# Tournament Flow

**Purpose:** the one product-level picture of how a Baseline tournament
moves from creation to completion. No technical detail — no field
names, no service names, no code — just the stages a real tournament
goes through and what happens at each one. For the technical
implementation, see `docs/ARCHITECTURE.md` and `docs/BACKLOG.md` Epic 2.

---

```
Create
  ↓
Open Registration
  ↓
Players Register
  ↓
Registration Closed
  ↓
Generate Matches
  ↓
IN_PROGRESS
  ↓
COMPLETED
```

---

## Create

An Admin, or a Coach organizing their own tournament, sets it up: a
name, where and when it happens, when registration closes, and how
many players it holds. Nobody can register yet — the tournament isn't
public until registration opens.

## Open Registration

The organizer opens the door. From this moment, players can see the
tournament and sign up.

## Players Register

Players browse open tournaments and register. They can also change
their mind and withdraw, right up until registration closes.

## Registration Closed

Registration closes the moment any one of three things happens first:
the registration deadline arrives, the tournament fills up, or the
organizer closes it manually. The moment it closes, every registered
player gets a confirmation — they're in, and they're told when and
where to show up.

### Current behaviour

Tournament registration deadlines are evaluated lazily. Evaluation
happens whenever Tournament Details are opened — by an Admin, a Coach,
or a Player. There is no background process watching the clock; the
deadline is only checked at the moment someone looks.

## Generate Matches

Once registration is closed, the organizer generates the matches.
Registered players are shuffled and paired up. This step needs an even
number of players — if the count is odd, the organizer adds or removes
one and tries again.

## IN_PROGRESS

The moment matches are generated, the tournament is underway. Players
play their matches like any other Baseline match — invite, confirm,
play.

## COMPLETED

Once the tournament has run its course, the organizer marks it
completed. A tournament can also be **cancelled** at any point before
completion, if it needs to stop early.

---

## Future Evolution

Tournament Platform v1 intentionally stops after COMPLETED. It gets
one real tournament organized start to finish — nothing more.

Future phases may include:

- Brackets
- Round Robin
- Standings
- Rankings
- Tournament Statistics
- Tournament History
- A dedicated Tournament Scheduler — evaluating deadlines on its own,
  without waiting for someone to open Tournament Details

Not for implementation now — this section exists so that reopening
this document later immediately shows where the module is heading,
without needing to reconstruct that from a backlog or chat history.
