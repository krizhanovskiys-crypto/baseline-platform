# Baseline Design System

This document captures the interaction patterns introduced during Sprint 7.x
(Available Matches, Profile redesign, Find Partner Smart Filter) so future
features reuse them instead of inventing new ones.

This is a living document — update it when a sprint introduces a new pattern,
not when it just reuses an existing one.

---

## Reuse UX before creating new UX

Before designing a new screen, check whether an existing pattern below
already solves the problem. Sprint 7.2 (Find Partner Smart Filter) reused
the Sprint 7.0 Filters pattern wholesale instead of inventing a new filter
UI. Sprint 7.1 (Edit Profile) reused the same pattern again. Inventing a
third variant would have fragmented the UX for no user benefit.

When a new field or flow looks similar to an existing one, prefer extending
the existing keyboard/handler (parametrize it) over writing a parallel copy.

---

## Search Mode pattern

When a feature could either run with sensible defaults or be narrowed first,
offer an explicit choice up front instead of guessing:

```
🔍 <Feature>

<Question — how would you like to proceed?>

[ Default / browse-everything option ]
[ Narrow / filter option ]
[ 🏠 Menu ]
```

Used by: Find Partner (`All Players` vs `Smart Filter`).

The "browse everything" branch must behave exactly as it did before the
Search Mode screen was introduced — it is a detour added in front of the
existing flow, not a rewrite of it.

---

## Filter pattern (main screen + category screens)

Two-level navigation for any screen with more than one independent filter
dimension:

**Main screen** — one row per category, each showing its current value, a
divider, then the primary action and Menu:

```
🎯 <Screen Title>

📍 Area: {current}
🎾 Courts: {current}
⭐ Level: {current}
────────────
✅ <Primary action>
🏠 Menu
```

**Category screen** — single column of options for one dimension, the
active option marked with a ✅ prefix, a back button at the bottom that
returns to the main screen without changing anything:

```
Choose <Category>

✅ Option A
Option B
Option C
⬅️ Filters
```

Tapping an option saves it and immediately returns to the main screen —
there is no intermediate confirmation step.

Used by: Available Matches Filters (Sprint 7.0), Find Partner Smart Filter
(Sprint 7.2, reusing the Area/Courts/Level selectors as-is).

Implementation note: the main screen and category screens are edited in
place (`edit_text`/`edit_reply_markup`), not re-sent as new messages, so
navigating back and forth doesn't spam the chat. Editing in place means
re-selecting the same value produces an identical message, which Telegram
rejects with "message is not modified" — every editor call must tolerate
that specific error (see "Edit-in-place tolerance" below).

A temporary filter selection (e.g. Smart Filter's Favourite Courts) is
stored only in FSM data and must never be written to the player's profile.
Only the dedicated profile-editing flow may persist changes.

---

## Edit Profile pattern

A read-only summary screen plus a separate editing screen, where every
field on the editing screen is itself a button into a single-field editor:

```
✏️ Edit Profile

👤 Name: {value}
⭐ Level: {value}
📍 Home Area: {value}
🎾 Favourite Courts: {value}
💬 Languages: {value}
────────────
🏠 Menu
```

Each field button reuses the existing selector for that field (Area, Level,
Courts) rather than duplicating a picker. Selecting a value saves
immediately and returns to Edit Profile — see "Automatic save" below.

---

## Automatic save

Editable fields save the moment a value is chosen. There is no separate
"Save" or "Confirm" button and no confirmation screen — the screen simply
returns to its parent with the new value already visible.

Exception: multi-select fields (Courts, Languages) use a "Done" button
because the save action only makes sense once, after all toggles are
finished — see "Multi-select with Done" below.

---

## Multi-select with Done

For any field where a player can choose more than one value (Favourite
Courts, Spoken Languages):

- Every option is always visible; selected options get a ✅ prefix.
- Tapping an option toggles it and re-renders the same screen (no
  navigation).
- A "Done" button commits the selection and returns to the parent screen.
  Nothing is saved before Done is pressed.

Used by: Courts (Edit Profile and, temporarily, Smart Filter), Languages
(Edit Profile).

---

## One Tap = One Result

Every button does exactly one obvious thing: open a screen, save a value,
or navigate back. Never combine "save" with "navigate to an unrelated
screen" behind one button, and never make a button's destination depend on
hidden state the player can't see on screen.

---

## Edit-in-place tolerance

Any handler that calls `edit_text` or `edit_reply_markup` as part of a
Filter/Edit-Profile-style flow must catch `TelegramBadRequest` and ignore it
when the message is `"message is not modified"`, re-raising anything else.
This is expected, not an error condition — see the Filter pattern above.
