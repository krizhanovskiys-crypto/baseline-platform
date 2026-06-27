"""Finite-state machine states for all bot conversation flows."""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """New-user onboarding wizard."""

    choose_language = State()
    choose_level = State()
    choose_area = State()
    choose_courts = State()


class CreateGameStates(StatesGroup):
    """Create-game wizard."""

    enter_court = State()
    choose_area = State()
    enter_date = State()
    enter_time = State()
    choose_type = State()
    choose_level = State()
    confirm = State()


class SettingsStates(StatesGroup):
    """Settings flow."""

    main = State()
    change_language = State()
    change_area = State()
    change_level = State()
    change_courts = State()
