"""Tests for Sprint 10.4 Phase 3 (UX Polish) — MVP items only.

1. Available Matches empty state keyboard — covered in test_available_matches.py.
2. Organize Match wizard step indicators (N/6).
3. Main Menu: "Available Now" renamed to "I'm Available".
4. Organize Match court step matches the Court Registry's "Add my own court" wording.
5. Header consistency (Choose vs Select, header+question formatting).

Also adds a regression test for the bug found while implementing item 3: a
handler's _TRIGGER_TEXTS set is a separate hardcoded copy of its main-menu
button text, and nothing enforces they stay in sync — Phase 2 renamed
btn_available_matches's emoji without updating available_matches.py's
_TRIGGER_TEXTS, silently breaking that button. This test catches that class
of drift for every _TRIGGER_TEXTS set in the app going forward.
"""
import backend.app.bot.handlers.available_matches as available_matches_handler
import backend.app.bot.handlers.available_now as available_now_handler
import backend.app.bot.handlers.find_partner as find_partner_handler
import backend.app.bot.handlers.my_matches as my_matches_handler
import backend.app.bot.handlers.organize_match as organize_match_handler
from backend.app.bot.texts import t

_LANGS = ["en", "uk", "ru"]

_TRIGGER_MODULE_TO_BUTTON_KEY = {
    available_matches_handler: "btn_available_matches",
    available_now_handler: "btn_available_now",
    find_partner_handler: "btn_find_partner",
    my_matches_handler: "btn_my_matches",
    organize_match_handler: "btn_organize_match",
}


def test_every_trigger_text_set_matches_its_main_menu_button_text():
    """Regression test for the class of bug found in Phase 3: a
    _TRIGGER_TEXTS set silently drifting from the button text that's
    supposed to trigger it, breaking the button with no test failure."""
    for module, button_key in _TRIGGER_MODULE_TO_BUTTON_KEY.items():
        expected = {t(button_key, lang) for lang in _LANGS}
        actual = module._TRIGGER_TEXTS
        assert actual == expected, (
            f"{module.__name__}._TRIGGER_TEXTS {actual} does not match "
            f"t('{button_key}', ...) values {expected}"
        )


# ── Item 3: Main Menu "Available Now" -> "I'm Available" ────────────────────────

def test_available_now_button_renamed():
    assert t("btn_available_now", "en") == "🔥 I'm Available"
    assert "Available Now" not in t("btn_available_now", "en")
    # Every locale keeps the 🔥 icon (unrelated to this rename).
    for lang in _LANGS:
        assert t("btn_available_now", lang).startswith("🔥")


# ── Item 2: Organize Match wizard step indicators ───────────────────────────────

def test_organize_match_steps_show_progress_indicator():
    """7 steps as of Sprint 11 Phase 1 (Match Discovery Refactor) — the
    new Area step is (3/7), pushing Court/Level/Players/Confirm down."""
    for lang in _LANGS:
        assert "(1/7)" in t("om_choose_date", lang)
        assert "(2/7)" in t("om_choose_time", lang)
        assert "(3/7)" in t("om_choose_area", lang)
        assert "(4/7)" in t("om_choose_court", lang)
        assert "(5/7)" in t("om_choose_level", lang, level=3.5)
        assert "(6/7)" in t("om_choose_players", lang)
        assert "(7/7)" in t(
            "om_confirm", lang, date_label="Today", time="18:00", court="X",
            level=3.5, players=2, match_type="Singles",
        )


def test_organize_match_step_headers_use_title_case_in_english():
    """The wizard's step headers were the only bold headers in the app using
    sentence case instead of Title Case, unlike every other screen title
    ("My Matches", "Edit Profile", "Confirm Match", ...)."""
    assert "*Choose Date*" in t("om_choose_date", "en")
    assert "*Choose Time*" in t("om_choose_time", "en")
    assert "*Choose Area*" in t("om_choose_area", "en")
    assert "*Choose Court*" in t("om_choose_court", "en")
    assert "*Number of Players*" in t("om_choose_players", "en")


# ── Item 4: Organize Match's court step matches the Court Registry wording ──────

def test_organize_match_custom_court_wording_matches_court_registry_standard():
    for lang in _LANGS:
        assert t("om_btn_other_court", lang) == t("btn_add_own_court", lang)


def test_organize_match_custom_court_prompt_matches_court_registry_standard():
    for lang in _LANGS:
        # Same structure as custom_court_prompt: "Enter the court name:" plus
        # an italic example line.
        assert "High Park Bubble" in t("om_enter_court", lang)


# ── Item 5: header consistency review ───────────────────────────────────────────

def test_choose_courts_uses_choose_not_select_in_english():
    """choose_language/level/area all say "Choose your X:" — choose_courts
    was the only one saying "Select" instead, in English only (uk/ru were
    already consistent with each other)."""
    assert t("choose_courts", "en", zone="Downtown").startswith("🏟 Choose your courts")
    assert "Select" not in t("choose_courts", "en", zone="Downtown")


def test_settings_header_matches_main_menu_question_style():
    """settings_header used to be "*Settings* — what would you like to
    change?" (em-dash, lowercase question) while main_menu uses a newline
    and a capitalized question — now both follow the same pattern."""
    for lang in _LANGS:
        menu = t("main_menu", lang)
        settings = t("settings_header", lang)
        assert "\n" in settings
        assert "—" not in settings
        menu_question = menu.split("\n", 1)[1]
        settings_question = settings.split("\n", 1)[1]
        assert menu_question[0] == settings_question[0]  # same capitalization style


def test_find_partner_search_mode_header_single_newline():
    """fp_search_mode_header used a blank line (\\n\\n) before its question
    while every other header+question screen (main_menu, settings_header)
    uses a single newline."""
    for lang in _LANGS:
        assert "\n\n" not in t("fp_search_mode_header", lang)
