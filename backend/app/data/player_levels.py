"""Level Groups Registry — the single source of truth for how NTRP
skill levels are grouped for browsing (Sprint 12.3 — Universal Player
Picker's "All Players" screen).

Configurable, not hardcoded per screen: add, remove, or resize a group
here and every caller (repository counts, pagination, the picker's own
keyboard) picks it up unchanged. Display labels are NOT stored here —
they're built via `t()` from `min_level`/`max_level` so they stay
translatable; this module only owns the numeric boundaries.

Pure, side-effect-free data (no ORM, no session) — same shape as
`courts.py`.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LevelGroup:
    min_level: float
    max_level: float | None  # None means "and above" (open-ended top group)


LEVEL_GROUPS: list[LevelGroup] = [
    LevelGroup(2.0, 2.5),
    LevelGroup(3.0, 3.5),
    LevelGroup(4.0, 4.5),
    LevelGroup(5.0, None),
]
