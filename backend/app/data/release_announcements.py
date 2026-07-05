"""Release Announcements Registry — the single source of truth for
what the "Baseline has been updated" / "What's New" screens show
(Sprint 13.1).

Adding a new release means adding one `Release` entry here — nothing
else in the announcement system changes. Existing entries are never
edited after the fact; the whole point of this registry is that a
past release's announcement stays exactly what shipped.

`Release` deliberately carries more than a bare list of strings —
`title` (a short, memorable name for the release, e.g. "Player
Platform") and structured `ReleaseChange(emoji, label)` entries — so a
future need (a release date, a category per change, a "highlight"
flag) is one more field on an existing dataclass, not an architecture
change.

Release content (title, change labels) is authored once, not per
language — same pattern as `RELEASE_NOTES.md` itself, which is
English-only. Only the screens' own static framing (headers, button
labels) is translated via `t()`; the change list is shown identically
to every player regardless of their language setting.

Pure, side-effect-free data (no ORM, no session) — same shape as
`courts.py` / `player_levels.py`.
"""
from dataclasses import dataclass

from backend.app.core.version import APP_VERSION


@dataclass(frozen=True)
class ReleaseChange:
    emoji: str  # e.g. "🏆"
    label: str  # e.g. "Coach Tournament Management"


@dataclass(frozen=True)
class Release:
    version: str  # must match backend.app.core.version.APP_VERSION exactly for the current release
    title: str  # short, memorable name for the release, e.g. "Player Platform"
    changes: list[ReleaseChange]


# Ordered oldest to newest. Never edit a past entry once it has shipped
# — only append. v0.13.0 covers everything that shipped under this
# version number: Sprint 12.2 (Coach UX Refactor) and Sprint 12.3
# (Player Platform Refactor) both shipped without their own version
# bump, so both are represented here — this is the app's one
# in-product announcement for v0.13.0, matching what
# RELEASE_NOTES.md's own v0.13.0 entry documents.
RELEASES: list[Release] = [
    Release(
        version="v0.13.0",
        title="Player Platform",
        changes=[
            ReleaseChange(emoji="🏆", label="Coach Tournament Management"),
            ReleaseChange(emoji="👥", label="Improved Player Cards"),
            ReleaseChange(emoji="🎾", label="Faster Player Picker"),
            ReleaseChange(emoji="🏅", label="Verified Coach Badges"),
        ],
    ),
]


def get_current_release() -> Release | None:
    """The release matching the app's own current APP_VERSION, if one
    is registered. None means the app was bumped without adding a
    matching Release entry here — the announcement system treats that
    as "nothing to announce" rather than guessing at content."""
    return next((r for r in RELEASES if r.version == APP_VERSION), None)


def display_version(version: str) -> str:
    """"v0.13.0" -> "0.13.0" for the user-facing "Version 0.13.0" line —
    APP_VERSION itself always keeps its "v" prefix everywhere else
    (Admin Dashboard, RELEASE_NOTES.md headers)."""
    return version[1:] if version.lower().startswith("v") else version
