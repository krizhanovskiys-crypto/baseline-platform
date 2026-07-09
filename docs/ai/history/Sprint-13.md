# Sprint History — Sprint 13

**Purpose:** archived detail for Sprint 13.1. Moved here from
`docs/ai/PROJECT_STATE.md`'s "Completed Major Features" list (Sprint
13.1 documentation refresh) so that file can stay a concise
current-state snapshot instead of a growing narrative. No information
was removed in the move.

---

## Release Announcements (Sprint 13.1)

An in-bot "what's new" screen shown automatically, once per version
bump, before the Main Menu, with no `/start` required.

**Storage:** `Player.last_seen_version` (nullable, migration
`9c75a6368f08`). A brand-new player is stamped with the current
`APP_VERSION` at creation — they joined on the newest version, nothing
to announce. Existing players stay `NULL` until they've actually seen
one, which is what makes backward compatibility work: every
pre-migration player sees the announcement exactly once, the next time
they interact.

**Release Notes source:** `data/release_announcements.py` —
`Release(version, title, changes: list[ReleaseChange(emoji, label)])`.
Structured from the start, not a bare list of strings, so a future
field (release date, category, a highlight flag) is one more attribute
on an existing dataclass, not an architecture change. Adding a release
is one new list entry; past entries are never edited.

**Architecture:** `ReleaseAnnouncementService` is the one place
`last_seen_version != APP_VERSION` is ever compared — the middleware
and the handler both call it, neither duplicates the check. Presenter
(`bot/presenters/release_announcement.py`) is pure, no I/O. Handler
(`bot/handlers/release_announcement.py`) only reacts to the two
`announce:*` callbacks — both screens' Continue buttons share one
callback since they do the identical thing. Middleware
(`bot/middlewares/release_announcement.py`), registered after
`DatabaseMiddleware`, intercepts any update — not just `/start` — when
a player's version is stale.

**Bug caught during runtime verification:** this middleware type
receives the outer `Update` object, not the inner `Message`/
`CallbackQuery` directly, unlike a router-level middleware — the first
version's `isinstance` checks silently never matched, so the
announcement never fired. The unit tests alone would not have caught
this; an end-to-end dispatcher test did.

**Content reconciliation:** v0.13.0's content was reconciled between
the in-app registry and `RELEASE_NOTES.md` after an initial draft
named two features that were never built (Tournament Results, viewing
player profiles from tournaments). Replaced with what actually
shipped — Coach Tournament Management, Improved Player Cards, Faster
Player Picker, Verified Coach Badges — and `RELEASE_NOTES.md`'s own
v0.13.0 entry (previously undocumented for Sprint 12.3) was brought in
line with it.

**Follow-up refinement:** the release's own internal `title` field
(e.g. "Player Platform") is deliberately not shown on either screen —
a sprint/internal release name isn't something a user benefits from;
what matters to them is what changed, not what the team called it
internally. The field stays on the `Release` model for documentation/
admin tooling/future use, just never rendered in the bot UI.

**Tests:** 472 total (455 existing + 17 new), covering first launch
after update, already-viewed version, no duplicate announcements,
version persistence, new-player and incomplete-profile edge cases,
both screens in all three languages, and two full end-to-end
dispatcher runs against the real database (since that's what the
middleware actually binds to).
