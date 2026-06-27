"""Inline and reply keyboard factories.

All keyboards are pure functions — no state, no side effects.
"""
import json
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from backend.app.bot.texts import AREAS, COURTS, SKILL_LEVELS, t


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=t("btn_find_partner", lang))
    builder.button(text=t("btn_create_game", lang))
    builder.button(text=t("btn_available_now", lang))
    builder.button(text=t("btn_my_profile", lang))
    builder.button(text=t("btn_settings", lang))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="lang:uk")
    builder.button(text="🇬🇧 English", callback_data="lang:en")
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.adjust(1)
    return builder.as_markup()


def skill_level_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in SKILL_LEVELS:
        builder.button(text=level, callback_data=f"level:{level}")
    builder.adjust(3)
    return builder.as_markup()


def area_keyboard(lang: str, callback_prefix: str = "area") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for area in AREAS:
        builder.button(text=area, callback_data=f"{callback_prefix}:{area}")
    builder.adjust(2)
    return builder.as_markup()


def courts_keyboard(lang: str, selected: list[str] | None = None) -> InlineKeyboardMarkup:
    """Multi-select court keyboard.  Selected courts get a ✅ prefix."""
    selected = selected or []
    builder = InlineKeyboardBuilder()
    for court in COURTS:
        label = f"✅ {court}" if court in selected else court
        builder.button(text=label, callback_data=f"court_toggle:{court}")
    builder.button(text=t("btn_done", lang), callback_data="courts_done")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Create Game
# ---------------------------------------------------------------------------

def match_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_singles", lang), callback_data="match_type:singles")
    builder.button(text=t("btn_doubles", lang), callback_data="match_type:doubles")
    builder.adjust(2)
    return builder.as_markup()


def game_level_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in SKILL_LEVELS:
        builder.button(text=level, callback_data=f"game_level:{level}")
    builder.button(text=t("btn_skip", lang), callback_data="game_level:skip")
    builder.adjust(3, 3, 1)
    return builder.as_markup()


def confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_confirm", lang), callback_data="game_confirm:yes")
    builder.button(text=t("btn_cancel", lang), callback_data="game_confirm:no")
    builder.adjust(2)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Find Partner
# ---------------------------------------------------------------------------

def partner_actions_keyboard(lang: str, partner_telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_invite", lang), callback_data=f"invite:{partner_telegram_id}")
    builder.button(text=t("btn_view_profile", lang), callback_data=f"view_profile:{partner_telegram_id}")
    builder.adjust(2)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Find Partner
# ---------------------------------------------------------------------------

def partner_card_keyboard(
    lang: str,
    username: str | None,
    show_next: bool,
) -> InlineKeyboardMarkup:
    """Keyboard shown under each partner card.

    Row 1: Contact (URL if username, else popup) + Next (if more players)
    Row 2: Menu
    """
    builder = InlineKeyboardBuilder()
    if username:
        builder.button(text=t("btn_contact", lang), url=f"https://t.me/{username}")
    else:
        builder.button(text=t("btn_contact", lang), callback_data="fp:no_contact")
    if show_next:
        builder.button(text=t("btn_next", lang), callback_data="fp:next")
    builder.button(text=t("btn_menu_home", lang), callback_data="fp:menu")
    builder.adjust(2 if show_next else 1, 1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_change_language", lang), callback_data="settings:language")
    builder.button(text=t("btn_change_area", lang), callback_data="settings:area")
    builder.button(text=t("btn_change_level", lang), callback_data="settings:level")
    builder.button(text=t("btn_change_courts", lang), callback_data="settings:courts")
    builder.adjust(2)
    return builder.as_markup()


def profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_edit_profile", lang), callback_data="profile:edit")
    return builder.as_markup()


def dev_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("dev_btn_create_players", lang), callback_data="dev:create_players")
    builder.button(text=t("dev_btn_reset_data", lang), callback_data="dev:reset_data")
    builder.button(text=t("dev_btn_stats", lang), callback_data="dev:stats")
    builder.button(text=t("dev_btn_exit", lang), callback_data="dev:exit")
    builder.adjust(1)
    return builder.as_markup()


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back_menu", lang), callback_data="menu:main")
    return builder.as_markup()
