"""Release Announcement presenter (Sprint 13.1) — builds the (text,
keyboard) pair for both announcement screens. Pure: takes an already-
fetched Release and a language, returns view artifacts only — no
session, no I/O, same discipline as
bot/presenters/tournament_details.py and bot/presenters/player_card.py.

Two screens:
    build_announcement_view()  "Baseline has been updated!" + Continue/What's New
    build_whats_new_view()     the change list + Continue

Both Continue buttons use the same callback_data ("announce:continue")
— they do the exact same thing (mark seen, show Main Menu), so there is
one handler for both, not two.
"""
from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backend.app.bot.texts import t
from backend.app.data.release_announcements import Release, display_version


@dataclass(frozen=True)
class AnnouncementView:
    text: str
    keyboard: InlineKeyboardMarkup


def build_announcement_view(lang: str, release: Release) -> AnnouncementView:
    """The release's own title is deliberately never shown on either
    screen — a sprint/internal release name isn't something a user
    benefits from; what matters to them is what changed, not what the
    team called it internally. Kept on the Release model itself for
    documentation, admin tooling, or future features — just not
    rendered here or on What's New below."""
    text = t("announcement_header", lang, version=display_version(release.version))
    builder = InlineKeyboardBuilder()
    builder.button(text=t("announcement_btn_continue", lang), callback_data="announce:continue")
    builder.button(text=t("announcement_btn_whats_new", lang), callback_data="announce:whats_new")
    builder.adjust(1)
    return AnnouncementView(text=text, keyboard=builder.as_markup())


def build_whats_new_view(lang: str, release: Release) -> AnnouncementView:
    header = t("whats_new_header", lang, version=display_version(release.version))
    change_lines = [f"{c.emoji} {c.label}" for c in release.changes]
    text = "\n\n".join([header, *change_lines])

    builder = InlineKeyboardBuilder()
    builder.button(text=t("whats_new_btn_continue", lang), callback_data="announce:continue")
    builder.adjust(1)
    return AnnouncementView(text=text, keyboard=builder.as_markup())
