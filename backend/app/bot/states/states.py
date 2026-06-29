"""Finite-state machine states for all bot conversation flows."""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """New-user onboarding wizard."""

    choose_language = State()
    choose_level = State()
    choose_area = State()
    choose_courts = State()



class OrganizeMatchStates(StatesGroup):
    """Organize-match guided wizard."""

    choose_date = State()
    enter_custom_date = State()
    choose_time = State()
    enter_custom_time = State()
    choose_court = State()
    enter_custom_court = State()
    choose_level = State()
    enter_custom_level = State()
    choose_players = State()
    confirm = State()


class FindPartnerStates(StatesGroup):
    """Find-partner browsing flow."""

    browsing = State()


class FindPlayersForMatchStates(StatesGroup):
    """Find-players-for-match browsing flow."""

    browsing = State()


class ConfirmMatchStates(StatesGroup):
    """Confirm-match wizard — collects optional organizer note before confirming."""

    enter_note = State()


class SettingsStates(StatesGroup):
    """Settings flow."""

    main = State()
    change_language = State()
    change_area = State()
    change_level = State()
    change_courts = State()
