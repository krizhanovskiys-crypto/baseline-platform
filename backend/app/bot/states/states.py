"""Finite-state machine states for all bot conversation flows."""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """New-user onboarding wizard."""

    choose_language = State()
    choose_level = State()
    choose_area = State()
    choose_courts = State()
    enter_custom_court = State()



class OrganizeMatchStates(StatesGroup):
    """Organize-match guided wizard. choose_area covers both its own
    "Use My Area"/"Change Area" screen and the full zone-list screen
    (om_area:use_mine / om_area:change / om_area_zone:{zone}) — one
    state, distinct callback_data, same pattern choose_court already
    uses for its own custom-entry escape hatch."""

    choose_date = State()
    enter_custom_date = State()
    choose_time = State()
    enter_custom_time = State()
    choose_area = State()
    choose_court = State()
    enter_custom_court = State()
    choose_level = State()
    enter_custom_level = State()
    choose_players = State()
    confirm = State()


class FindPartnerStates(StatesGroup):
    """Find-partner flow. browsing = paginating cards; smart_filter = the
    Sprint 7.0-style filter screens shown before the search runs;
    enter_custom_court = free-text entry for "Add my own court" within the
    Smart Filter's Favourite Courts step."""

    browsing = State()
    smart_filter = State()
    enter_custom_court = State()


class FindPlayersForMatchStates(StatesGroup):
    """Find-players-for-match browsing flow."""

    browsing = State()


class AvailableMatchesStates(StatesGroup):
    """Available-matches browsing flow. Stores current_page and filters in FSM data."""

    browsing = State()


class ConfirmMatchStates(StatesGroup):
    """Confirm-match wizard — collects optional organizer note before confirming."""

    enter_note = State()


class AdminAuthStates(StatesGroup):
    """Admin Center PIN entry — /dev prompts this only for a confirmed
    operator with no active session and no active lockout."""

    enter_pin = State()


class AdminPlayersStates(StatesGroup):
    """Admin Center Players module. browsing stores current_page in FSM
    data (same pattern as AvailableMatchesStates); enter_search is the
    free-text Search Player input."""

    browsing = State()
    enter_search = State()


class CreateTournamentStates(StatesGroup):
    """Create/Edit Tournament wizard (Admin Center + Verified Coach's
    Tournament Center) — mirrors OrganizeMatchStates' step shape."""

    enter_name = State()
    choose_area = State()
    choose_court = State()
    enter_custom_court = State()
    enter_date = State()
    enter_time = State()
    enter_deadline = State()
    enter_max_players = State()
    confirm = State()


class TournamentBrowseStates(StatesGroup):
    """Player-facing Browse Tournaments — stores current_page in FSM
    data, same pattern as AvailableMatchesStates/AdminPlayersStates."""

    browsing = State()


class AdminTournamentsStates(StatesGroup):
    """Admin Center / Tournament Center — Browse Tournaments
    pagination. Add Player's own search prompt is now
    PlayerPickerStates.enter_search (Sprint 12.3 — Universal Player
    Picker), not a Tournament-specific state."""

    browsing = State()


class MyTournamentsStates(StatesGroup):
    """Verified Coach's My Tournaments (Sprint 12.2) — reached from the
    Main Menu's role-aware Tournament Menu, not /dev. Same
    tourn:page:N pagination callback pattern as TournamentBrowseStates/
    AdminTournamentsStates, gated by its own state so all three coexist
    without collision."""

    browsing = State()


class PlayerPickerStates(StatesGroup):
    """Universal Player Picker (Sprint 12.3) — a reusable component,
    not owned by Tournament. FSM data carries which consumer is active
    (picker_context_type, e.g. "tournament_add_player", plus whatever
    id that consumer needs) and, once a level group is opened, which
    group/page, so selecting a player can return to the same list
    afterward rather than the beginning."""

    enter_search = State()
    browsing_levels = State()
    browsing_players = State()


class SettingsStates(StatesGroup):
    """Settings / Edit Profile field-editing flow."""

    main = State()
    change_language = State()
    change_area = State()
    change_level = State()
    choose_courts_zone = State()
    change_courts = State()
    enter_custom_court = State()
    change_name = State()
    change_languages = State()
