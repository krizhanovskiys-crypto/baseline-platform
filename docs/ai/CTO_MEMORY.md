# CTO Memory

**Purpose:** permanent truths only. No explanations, no dates, no
sprint numbers — if it can go stale, it doesn't belong here. When a
truth here is ever contradicted by a real, approved decision, remove or
rewrite the line; never let two contradictory lines coexist.

---

- Business logic lives only in Services. Handlers never touch a
  repository directly.
- Existing Match uses Match Context. Find Partner uses Player Context.
- `OperatorPermission` is independent from `Player`.
- `PermissionService` never authenticates.
- `AdminSessionService` never authorizes.
- Never duplicate repositories — extend the existing one per model.
- Always escape user-entered text before it reaches a
  `parse_mode`-rendered message.
- Rating/ELO/reputation permanently rejected — explicit product
  non-goal.
- Dashboard architecture is frozen — it is the permanent root screen;
  modules plug a button into it, they never grow its layout.
- Players module completed — the reference shape for every future
  Admin Center record module.
- Every Admin Center record module = Search → Browse → Details →
  Actions.
- Back always returns to a module's own Root, never the exact prior
  screen.
- Admin Center is a package (`handlers/admin/`), never a single growing
  file.
- Court Registry is data, not a database table — a pure lookup module.
- `MatchLifecycleService` is the sole authority over `Game.status`.
- No forced migrations for UI/vocabulary changes.
- Never commit or push without explicit approval.
