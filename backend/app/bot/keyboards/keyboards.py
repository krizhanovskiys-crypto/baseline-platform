"""Inline and reply keyboard factories.

All keyboards are pure functions — no state, no side effects.
"""
import json
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from backend.app.bot.texts import SKILL_LEVELS, SPOKEN_LANGUAGES, t
from backend.app.data.courts import TENNIS_ZONES, get_courts_for_zone
from backend.app.schemas.player import PlayerRead


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=t("btn_find_partner", lang))
    builder.button(text=t("btn_organize_match", lang))
    builder.button(text=t("btn_available_now", lang))
    builder.button(text=t("btn_available_matches", lang))
    builder.button(text=t("btn_my_matches", lang))
    builder.button(text=t("btn_my_profile", lang))
    builder.button(text=t("btn_settings", lang))
    builder.adjust(2, 2, 2, 1)
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
    """Tennis Zone selector. Despite the name (kept for callback/state
    compatibility across the codebase), options come from the Court
    Registry's TENNIS_ZONES — Baseline uses Tennis Zones, not administrative
    districts."""
    builder = InlineKeyboardBuilder()
    for zone in TENNIS_ZONES:
        builder.button(text=zone, callback_data=f"{callback_prefix}:{zone}")
    builder.adjust(2)
    return builder.as_markup()


def courts_keyboard(lang: str, zone: str, selected: list[str] | None = None) -> InlineKeyboardMarkup:
    """Multi-select court keyboard scoped to one Tennis Zone.

    Registry courts for `zone` (Court Registry — backend/app/data/courts.py
    — is the single source of truth) are shown first. Any already-selected
    court that ISN'T part of that zone's registry — typically a custom
    court added via "Add my own court", but also simply a court saved while
    a different zone was open — is rendered in a separate "Custom Courts"
    section below, so it's visible and already checked immediately, not
    just confirmed via a message. Every button, registry or custom, toggles
    through the same court_toggle:{court} callback — callers don't need a
    separate code path or FSM state for custom courts.
    """
    selected = selected or []
    zone_courts = get_courts_for_zone(zone)
    custom_courts = [court for court in selected if court not in zone_courts]

    builder = InlineKeyboardBuilder()
    rows: list[int] = []

    for court in zone_courts:
        label = f"✅ {court}" if court in selected else court
        builder.button(text=label, callback_data=f"court_toggle:{court}")
    rows.extend([2] * (len(zone_courts) // 2) + ([1] if len(zone_courts) % 2 else []))

    if custom_courts:
        builder.button(text=t("custom_courts_divider", lang), callback_data="noop")
        rows.append(1)
        for court in custom_courts:
            builder.button(text=f"✅ {court}", callback_data=f"court_toggle:{court}")
        rows.extend([1] * len(custom_courts))

    builder.button(text=t("btn_add_own_court", lang), callback_data="court_add_custom")
    builder.button(text=t("btn_done", lang), callback_data="courts_done")
    rows.extend([1, 1])

    builder.adjust(*rows)
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


def search_mode_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Find Partner entry screen: choose between browsing everyone or Smart Filter."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("fp_btn_all_players", lang), callback_data="fp:mode:all")
    builder.button(text=t("fp_btn_smart_filter", lang), callback_data="fp:mode:smart")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def smart_filter_keyboard(lang: str, filters: dict[str, object], home_area: str) -> InlineKeyboardMarkup:
    """Smart Filter main screen — same UX as the Sprint 7.0 Available Matches
    Filters screen (category rows showing current value, divider, action,
    Menu), scoped to Find Partner's three approved fields."""
    area_value = home_area if filters.get("area", "home") == "home" else filters.get("area")
    courts_value = ", ".join(filters.get("courts") or []) or "—"
    level_labels = {"default": "±0.5", "1.0": "±1.0", "any": t("available_matches_filter_any", lang)}
    level_value = level_labels.get(filters.get("level", "default"), "±0.5")

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{t('available_matches_filter_area', lang)}: {area_value}",
        callback_data="fp:smartfilter:open:area",
    )
    builder.button(
        text=f"{t('edit_profile_field_courts', lang)}: {courts_value}",
        callback_data="fp:smartfilter:open:courts",
    )
    builder.button(
        text=f"{t('available_matches_filter_level', lang)}: {level_value}",
        callback_data="fp:smartfilter:open:level",
    )
    builder.button(text="────────────", callback_data="noop")
    builder.button(text=t("smart_filter_btn_find", lang), callback_data="fp:smartfilter:apply")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1, 1, 1, 1, 1)
    return builder.as_markup()


def level_tolerance_keyboard(
    lang: str, selected: str, callback_prefix: str, back_callback: str
) -> InlineKeyboardMarkup:
    """Single-column ±tolerance selector (±0.5 / ±1.0 / Any), following the same
    convention as available_matches_filter_category_keyboard's level screen.
    `selected` is one of "default" (±0.5) / "1.0" / "any"."""
    def _mark(label: str, value: str) -> str:
        return f"✅ {label}" if value == selected else label

    builder = InlineKeyboardBuilder()
    builder.button(text=_mark("±0.5", "default"), callback_data=f"{callback_prefix}:default")
    builder.button(text=_mark("±1.0", "1.0"), callback_data=f"{callback_prefix}:1.0")
    builder.button(
        text=_mark(t("available_matches_filter_any", lang), "any"), callback_data=f"{callback_prefix}:any"
    )
    builder.button(text=t("available_matches_btn_back_to_filters", lang), callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Settings now covers only interface language — profile fields (area,
    level, courts, name, spoken languages) are edited via Edit Profile."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_change_language", lang), callback_data="settings:language")
    builder.adjust(1)
    return builder.as_markup()


def profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_edit_profile", lang), callback_data="profile:edit")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Edit Profile
# ---------------------------------------------------------------------------

def edit_profile_keyboard(lang: str, player: PlayerRead) -> InlineKeyboardMarkup:
    """Main Edit Profile screen: one row per field showing its current value,
    a divider, then Menu. Tapping a field row opens its edit flow — Level/Area/
    Courts reuse the existing settings:* callbacks (no duplicate handlers)."""
    courts_display = ", ".join(player.preferred_courts or []) or "—"
    languages_display = ", ".join(player.spoken_languages or []) or "—"

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{t('edit_profile_field_name', lang)}: {player.first_name}",
        callback_data="editprofile:name",
    )
    builder.button(
        text=f"{t('edit_profile_field_level', lang)}: {player.skill_level}",
        callback_data="settings:level",
    )
    builder.button(
        text=f"{t('edit_profile_field_area', lang)}: {player.home_area or '—'}",
        callback_data="settings:area",
    )
    builder.button(
        text=f"{t('edit_profile_field_courts', lang)}: {courts_display}",
        callback_data="settings:courts",
    )
    builder.button(
        text=f"{t('edit_profile_field_languages', lang)}: {languages_display}",
        callback_data="editprofile:languages",
    )
    builder.button(text="────────────", callback_data="noop")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1, 1, 1, 1, 1, 1)
    return builder.as_markup()


def spoken_languages_keyboard(lang: str, selected: list[str] | None = None) -> InlineKeyboardMarkup:
    """Multi-select spoken-languages keyboard. Selected languages get a ✅
    prefix (same convention as courts_keyboard). Add entries to
    texts.SPOKEN_LANGUAGES to support more languages — no code change here."""
    selected = selected or []
    builder = InlineKeyboardBuilder()
    for spoken_lang in SPOKEN_LANGUAGES:
        label = f"✅ {spoken_lang}" if spoken_lang in selected else spoken_lang
        builder.button(text=label, callback_data=f"language_toggle:{spoken_lang}")
    builder.button(text=t("btn_done", lang), callback_data="languages_done")

    n = len(SPOKEN_LANGUAGES)
    rows = [2] * (n // 2) + ([1] if n % 2 else []) + [1]  # options in pairs, Done on its own row
    builder.adjust(*rows)
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
    builder.button(text=t("om_btn_my_matches", lang), callback_data="my_matches:back")
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


# ---------------------------------------------------------------------------
# Game-full organizer notification
# ---------------------------------------------------------------------------

def game_full_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard sent to the organizer when a match becomes full.

    Cancel uses the same match:cancel: callback as Match Details' Cancel
    Match button — one Cancel Match flow (confirmation + notification),
    not two independent implementations.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t("game_full_btn_confirm", lang), callback_data=f"confirm_match:{game_id}")
    builder.button(text=t("game_full_btn_players", lang), callback_data=f"view_game:{game_id}")
    builder.button(text=t("game_full_btn_cancel", lang), callback_data=f"match:cancel:{game_id}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_note_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard shown when asking the organizer for an optional note."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("confirm_btn_skip", lang), callback_data="confirm_note:skip")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

def invitation_keyboard(lang: str, invitation_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("inv_btn_accept", lang), callback_data=f"inv:accept:{invitation_id}")
    builder.button(text=t("inv_btn_decline", lang), callback_data=f"inv:decline:{invitation_id}")
    builder.adjust(2)
    return builder.as_markup()


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back_menu", lang), callback_data="menu:main")
    return builder.as_markup()


def my_match_card_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown under each upcoming match card."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("my_matches_btn_open", lang), callback_data=f"match:open:{game_id}")
    return builder.as_markup()


def leave_match_done_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard shown after a player successfully leaves a match."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("match_details_btn_back", lang), callback_data="my_matches:back")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1)
    return builder.as_markup()


def cancel_match_confirm_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard for the Cancel Match confirmation screen: Yes / No.

    "No" returns to Match Details (match:open:{game_id}) rather than
    cancelling anything — same pattern as join_confirmation_keyboard.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t("cancel_match_confirm_yes", lang), callback_data=f"match:cancel_confirm:{game_id}")
    builder.button(text=t("cancel_match_confirm_no", lang), callback_data=f"match:open:{game_id}")
    builder.adjust(2)
    return builder.as_markup()


def view_roster_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown under the View Roster screen — returns to this
    specific match's details, not just the main menu (UX-24)."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back_to_match_details", lang), callback_data=f"match:open:{game_id}")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1)
    return builder.as_markup()


def match_details_keyboard(lang: str, role: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown under the Match Details card. Role: 'organizer', 'participant', 'other'."""
    builder = InlineKeyboardBuilder()
    if role == "organizer":
        builder.button(text=t("match_details_btn_add_player", lang), callback_data=f"fpm:start:{game_id}")
        builder.button(text=t("match_details_btn_cancel_match", lang), callback_data=f"match:cancel:{game_id}")
        builder.button(text=t("match_details_btn_back", lang), callback_data="my_matches:back")
        builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
        builder.adjust(1, 1, 2)
    elif role == "participant":
        builder.button(text=t("match_details_btn_leave_match", lang), callback_data=f"match:leave:{game_id}")
        builder.button(text=t("match_details_btn_back", lang), callback_data="my_matches:back")
        builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
        builder.adjust(1, 2)
    else:
        builder.button(text=t("match_details_btn_join_match", lang), callback_data=f"match:join:{game_id}")
        builder.button(text=t("match_details_btn_back", lang), callback_data="my_matches:back")
        builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
        builder.adjust(1, 2)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Available Matches
# ---------------------------------------------------------------------------

def available_match_card_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown under each Available Matches card. Reuses the existing
    Match Details entry point (match:open:{game_id})."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("available_matches_btn_view_details", lang), callback_data=f"match:open:{game_id}")
    return builder.as_markup()


def available_matches_nav_keyboard(
    lang: str, page: int, has_prev: bool, has_next: bool
) -> InlineKeyboardMarkup:
    """Bottom keyboard for the Available Matches list: Filters / Previous / Next / Home."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("available_matches_btn_filters", lang), callback_data="available:filters")
    row2 = 0
    if has_prev:
        builder.button(text=t("available_matches_btn_prev", lang), callback_data=f"available:page:{page - 1}")
        row2 += 1
    if has_next:
        builder.button(text=t("available_matches_btn_next", lang), callback_data=f"available:page:{page + 1}")
        row2 += 1
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    sizes = [1] + ([row2] if row2 else []) + [1]
    builder.adjust(*sizes)
    return builder.as_markup()


def available_matches_empty_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for the Available Matches empty state — without this, a
    zero-results page had no buttons at all (Phase 3 UX review, item 1)."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("available_matches_btn_filters", lang), callback_data="available:filters")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")
    builder.adjust(1, 1)
    return builder.as_markup()


def _filter_display_value(lang: str, dimension: str, filters: dict[str, object], home_area: str) -> str:
    """Return the localized current-value label for one filter category."""
    if dimension == "area":
        value = filters.get("area", "home")
        if value == "any":
            return t("available_matches_filter_any", lang)
        if value in (None, "home"):
            return home_area
        return str(value)
    if dimension == "date":
        value = filters.get("date", "today")
        return t("om_btn_today", lang) if value == "today" else t("available_matches_filter_any", lang)
    if dimension == "level":
        value = filters.get("level", "default")
        return "±0.5" if value == "default" else t("available_matches_filter_any", lang)
    if dimension == "type":
        value = filters.get("match_type")
        if value == "singles":
            return t("om_match_type_singles", lang)
        if value == "doubles":
            return t("om_match_type_doubles", lang)
        return t("available_matches_filter_any", lang)
    raise ValueError(f"Unknown filter dimension: {dimension}")


_CATEGORY_LABEL_KEYS = [
    ("area", "available_matches_filter_area"),
    ("level", "available_matches_filter_level"),
    ("date", "available_matches_filter_date"),
    ("type", "available_matches_filter_match_type"),
]


def available_matches_filters_keyboard(
    lang: str, filters: dict[str, object], home_area: str
) -> InlineKeyboardMarkup:
    """Main Filters screen: one row per category showing its current value
    (e.g. "📍 Area: Downtown"), a divider, then Apply / Menu. Tapping a
    category row opens its dedicated selection screen
    (available:filters:open:{dimension}). Menu uses the project's standard
    return-to-main-menu pattern (same text/callback as every other "🏠 Menu"
    button — see match_details_keyboard, leave_match_done_keyboard, etc.)."""
    builder = InlineKeyboardBuilder()
    for dimension, label_key in _CATEGORY_LABEL_KEYS:
        label = t(label_key, lang)
        value = _filter_display_value(lang, dimension, filters, home_area)
        builder.button(text=f"{label}: {value}", callback_data=f"available:filters:open:{dimension}")

    builder.button(text="────────────", callback_data="noop")
    builder.button(text=t("available_matches_btn_apply", lang), callback_data="available:filters:apply")
    builder.button(text=t("btn_menu_home", lang), callback_data="menu:main")

    builder.adjust(1, 1, 1, 1, 1, 1, 1)
    return builder.as_markup()


def available_matches_filter_category_keyboard(
    lang: str, dimension: str, filters: dict[str, object], home_area: str
) -> InlineKeyboardMarkup:
    """Single-column selection screen for one filter category (area/date/level/type).
    The currently-selected option is marked with a ✅ prefix. "⬅️ Filters" returns
    to the main Filters screen (available:filters:back) without changing any value."""
    def _mark(label: str, selected: bool) -> str:
        return f"✅ {label}" if selected else label

    builder = InlineKeyboardBuilder()

    if dimension == "area":
        selected_area = home_area if filters.get("area", "home") in (None, "home") else filters.get("area")
        for area in TENNIS_ZONES:
            builder.button(text=_mark(area, area == selected_area), callback_data=f"available:filter:area:{area}")
        builder.button(
            text=_mark(t("available_matches_filter_any", lang), filters.get("area") == "any"),
            callback_data="available:filter:area:any",
        )
    elif dimension == "date":
        selected_date = filters.get("date", "today")
        builder.button(
            text=_mark(t("om_btn_today", lang), selected_date == "today"),
            callback_data="available:filter:date:today",
        )
        builder.button(
            text=_mark(t("available_matches_filter_any", lang), selected_date == "any"),
            callback_data="available:filter:date:any",
        )
    elif dimension == "level":
        selected_level = filters.get("level", "default")
        builder.button(
            text=_mark("±0.5", selected_level == "default"), callback_data="available:filter:level:default"
        )
        builder.button(
            text=_mark(t("available_matches_filter_any", lang), selected_level == "any"),
            callback_data="available:filter:level:any",
        )
    elif dimension == "type":
        selected_type = filters.get("match_type")
        builder.button(
            text=_mark(t("available_matches_filter_any", lang), selected_type is None),
            callback_data="available:filter:type:any",
        )
        builder.button(
            text=_mark(t("om_match_type_singles", lang), selected_type == "singles"),
            callback_data="available:filter:type:singles",
        )
        builder.button(
            text=_mark(t("om_match_type_doubles", lang), selected_type == "doubles"),
            callback_data="available:filter:type:doubles",
        )
    else:
        raise ValueError(f"Unknown filter dimension: {dimension}")

    builder.button(text=t("available_matches_btn_back_to_filters", lang), callback_data="available:filters:back")
    builder.adjust(1)
    return builder.as_markup()


def join_confirmation_keyboard(lang: str, game_id: int) -> InlineKeyboardMarkup:
    """Keyboard for the Join Confirmation screen: Join / Cancel."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("join_confirm_btn_join", lang), callback_data=f"available:confirm:{game_id}")
    builder.button(text=t("join_confirm_btn_cancel", lang), callback_data=f"match:open:{game_id}")
    builder.adjust(2)
    return builder.as_markup()
