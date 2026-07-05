"""Universal Player Card presenter (Sprint 12.3) — the one place a
player's own card is rendered. Every screen that shows a player's
profile-shaped card (My Profile, Find Partner, Available Now, Find
Players for a Match, Tournament's Add Player results, Admin Player
Details) must call this, not implement its own formatting.

Pure: takes a PlayerRead (already fetched) and returns text only — no
session, no I/O, same discipline as
bot/presenters/tournament_details.py.

Badges are a list, not an if/else chain, on purpose: `_BADGES` is the
one place that answers "what badges exist and in what order" — a
future badge (Club Organizer 🏆, Tournament Champion 🥇, Top Player ⭐,
...) is one more `Badge(...)` entry here, once PlayerRead grows the
matching boolean field. Nothing in build_player_card_text() itself, or
any of its callers, changes when a badge is added — only this list
does. Today there is genuinely only one (Verified Coach); the shape is
already built for many.
"""
from dataclasses import dataclass

from aiogram.utils.markdown import markdown_decoration

from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead

_EMPTY = "—"


@dataclass(frozen=True)
class Badge:
    attribute: str  # the PlayerRead boolean field that turns this badge on
    text_key: str  # the texts.py key rendering this badge's own line


# Evaluated in this order; each renders only if getattr(player, attribute)
# is truthy. This is the single list a future badge is added to — see the
# module docstring above.
_BADGES: list[Badge] = [
    Badge(attribute="is_verified_coach", text_key="player_card_badge_verified_coach"),
]


def _format_level(level: float | None) -> str:
    return f"{level:.1f}" if level is not None else _EMPTY


def _join(values: list[str] | None) -> str:
    return " • ".join(values) if values else _EMPTY


def _join_escaped(values: list[str] | None) -> str:
    """Favourite Courts can include custom, free-text court names
    (docs/PRODUCT_DECISIONS.md's escaping rule) — each one is escaped
    individually before joining, same as first_name."""
    if not values:
        return _EMPTY
    return " • ".join(markdown_decoration.quote(v) for v in values)


def build_player_card_text(lang: str, player: PlayerRead) -> str:
    """Standard order, always: Name, badges (only those that apply, in
    _BADGES' order), Level, Languages, Favourite Courts, Matches.
    Callers needing extra, screen-specific context (e.g. Admin Player
    Details' telegram_id/registration date) append their own lines
    after this block — they never reorder or reformat what's inside
    it."""
    lines = [t("player_card_name", lang, name=markdown_decoration.quote(player.first_name))]
    for badge in _BADGES:
        if getattr(player, badge.attribute, False):
            lines.append(t(badge.text_key, lang))
    lines.append(t("player_card_level", lang, level=_format_level(player.skill_level)))
    lines.append(t("player_card_languages", lang, languages=_join(player.spoken_languages)))
    lines.append(t("player_card_courts", lang, courts=_join_escaped(player.preferred_courts)))
    lines.append(t("player_card_matches", lang, matches=player.matches_played))
    return "\n".join(lines)
