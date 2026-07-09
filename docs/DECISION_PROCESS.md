# Baseline — Decision Process

Two kinds of decisions from here on. Every future document should say which one it is in its title.

---

### Architecture Decision (ADR)
**Rare.** Changes the foundation — Domain, API contract shape, Identity. The kind of thing that, if wrong, means rewriting things that already have code and tests depending on them.

Examples already made: staying on `/api/v1`, Telegram-only identity, Standings scoped per-tournament not accumulated.

### Product Decision (PD)
**Frequent.** How the product behaves, within a foundation that's already stable. Who does an action, what's shown, what's out of scope for now. Reversible without touching Domain or API shape — usually just service-layer logic or a UI rule.

Examples: who reports a match result, who can create a Tournament, whether score detail is shown, whether a tiebreak is required.

---

**Why this split matters now, not before:** while the architecture itself was still moving, every decision was structural by definition — there was no "foundation" yet to be stable *against*. Now that UX, Design System, API, and Domain Model are locked, most new questions are actually about product behavior sitting on top of that foundation, not about the foundation itself. Calling a product rule an "architecture decision" overstates its weight and invites re-litigating the whole stack every time; calling it what it is keeps the team's attention on the one or two decisions per sprint that actually deserve that level of scrutiny.

**In practice:** if a new question can be answered without touching `Baseline_Domain_Model.md` or `Baseline_API_v2_Architecture.md`, it's a PD. If answering it *requires* changing either of those documents, it's an ADR — and per the rule already established, those should now be rare.
