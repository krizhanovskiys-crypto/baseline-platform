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
    builder.button(text=t("btn_organize_match", lang))
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


# ---------------------------------------------------------------------------
# Organize Match
# ---------------------------------------------------------------------------

def om_date_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("om_btn_today", lang), callback_data="om_date:today")
    builder.button(text=t("om_btn_tomorrow", lang), callback_data="om_date:tomorrow")
    builder.button(text=t("om_btn_other_date", lang), callback_data="om_date:other")
    builder.adjust(2, 1)
    return builder.as_markup()


def om_time_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for hour in ["18:00", "19:00", "20:00"]:
        builder.button(text=hour, callback_data=f"om_time:{hour}")
    builder.button(text=t("om_btn_other_time", lang), callback_data="om_time:other")
    builder.adjust(3, 1)
    return builder.as_markup()


def om_court_keyboard(lang: str, courts: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, court in enumerate(courts):
        builder.button(text=court, callback_data=f"om_court:{i}")
    builder.button(text=t("om_btn_other_court", lang), callback_data="om:court_custom")
    builder.adjust(2)
    return builder.as_markup()


def om_level_keyboard(lang: str, current_level: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("om_btn_use_my_level", lang, level=current_level), callback_data="om_level:use_mine")
    builder.button(text=t("om_btn_change_level", lang), callback_data="om_level:change")
    builder.adjust(1)
    return builder.as_markup()


def om_players_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="2", callback_data="om_players:2")
    builder.button(text="4", callback_data="om_players:4")
    builder.adjust(2)
    return builder.as_markup()


def om_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("om_btn_confirm", lang), callback_data="om:confirm")
    builder.button(text=t("btn_cancel", lang), callback_data="om:cancel")
    builder.adjust(2)
    return builder.as_markup()


def om_success_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("om_btn_find_players", lang), callback_data=f"fpm:start:{game_id}")
    builder.button(text=t("om_btn_my_matches", lang), callback_data="om:my_matches")
    builder.button(text=t("btn_menu_home", lang), callback_data="om:menu")
    builder.adjust(2, 1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Find Players for Match
# ---------------------------------------------------------------------------

def fpm_card_keyboard(
    lang: str,
    player_id: int,
    show_prev: bool,
    show_next: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("fpm_btn_select", lang), callback_data=f"fpm:select:{player_id}")
    if show_prev:
        builder.button(text=t("fpm_btn_prev", lang), callback_data="fpm:prev")
    if show_next:
        builder.button(text=t("fpm_btn_next", lang), callback_data="fpm:next")
    builder.button(text=t("btn_menu_home", lang), callback_data="fpm:menu")
    nav_count = (1 if show_prev else 0) + (1 if show_next else 0)
    if nav_count == 2:
        builder.adjust(1, 2, 1)
    elif nav_count == 1:
        builder.adjust(1, 1, 1)
    else:
        builder.adjust(1, 1)
    return builder.as_markup()


def fpm_after_select_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("fpm_btn_continue", lang), callback_data="fpm:continue")
    builder.button(text=t("fpm_btn_view_selected", lang), callback_data="fpm:view_selected")
    builder.button(text=t("btn_menu_home", lang), callback_data="fpm:menu")
    builder.adjust(1)
    return builder.as_markup()


def fpm_selected_list_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("fpm_btn_back", lang), callback_data="fpm:back")
    builder.button(text=t("btn_menu_home", lang), callback_data="fpm:menu")
    builder.adjust(2)
    return builder.as_markup()


def fpm_empty_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_menu_home", lang), callback_data="fpm:menu")
    return builder.as_markup()


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back_menu", lang), callback_data="menu:main")
    return builder.as_markup()
