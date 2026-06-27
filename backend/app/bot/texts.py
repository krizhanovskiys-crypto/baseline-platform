"""UI text strings for the Telegram bot, keyed by language code."""
from typing import Literal

Language = Literal["en", "uk", "ru"]

_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        # Onboarding
        "welcome_new": "👋 Welcome to *Baseline* — the tennis matchmaking platform!\n\nLet's set up your profile.",
        "welcome_back": "👋 Welcome back, *{name}*!",
        "choose_language": "🌍 Choose your language:",
        "choose_level": "🎾 Choose your skill level (NTRP):",
        "choose_area": "📍 Choose your home area:",
        "choose_courts": "🏟 Select your preferred courts (tap to toggle, then tap ✅ Done):",
        "profile_complete": "✅ Profile complete! Welcome to Baseline.",
        # Main menu
        "main_menu": "🎾 *Main Menu*\nWhat would you like to do?",
        "btn_find_partner": "🎾 Find Partner",
        "btn_create_game": "📅 Create Game",
        "btn_available_now": "🔥 Available Now",
        "btn_my_profile": "👤 My Profile",
        "btn_settings": "⚙️ Settings",
        # Find partner
        "finding_partners": "🔍 Searching for partners in *{area}* at level *{level}* ±0.5...",
        "no_partners": (
            "🎾 We haven't found your ideal tennis partner yet.\n\n"
            "🌱 The Baseline community is growing every day.\n\n"
            "🎁 Invite a friend to Baseline — they might be your next opponent on the court."
        ),
        "partner_card": "👤 *{name}*\nLevel: {level}\nArea: {area}\nRating: {rating:.0f}",
        "btn_invite": "✉️ Invite",
        "btn_view_profile": "👀 View Profile",
        "invite_sent": "✉️ Invitation sent to {name}!",
        # Create game
        "cg_enter_court": "🏟 *Step 1/5* — Enter court name or address:",
        "cg_enter_area": "📍 *Step 2/5* — Choose the area:",
        "cg_enter_date": "📅 *Step 3/5* — Enter the date (DD.MM.YYYY):",
        "cg_enter_time": "🕐 *Step 4/5* — Enter the time (HH:MM):",
        "cg_choose_type": "🎾 *Step 5a/5* — Singles or Doubles?",
        "cg_choose_level": "📊 *Step 5b/5* — Required level (or skip):",
        "cg_confirm": (
            "✅ *Confirm Game*\n\n"
            "🏟 Court: {court}\n"
            "📍 Area: {area}\n"
            "📅 Date: {date}\n"
            "🕐 Time: {time}\n"
            "🎾 Type: {match_type}\n"
            "📊 Level: {level}\n\n"
            "Create this game?"
        ),
        "cg_created": "🎉 Game created! ID: #{game_id}",
        "cg_error_date": "❌ Invalid date. Please use DD.MM.YYYY format.",
        "cg_error_time": "❌ Invalid time. Please use HH:MM format.",
        "btn_singles": "1️⃣ Singles",
        "btn_doubles": "2️⃣ Doubles",
        "btn_confirm": "✅ Confirm",
        "btn_cancel": "❌ Cancel",
        "btn_skip": "⏭ Skip",
        "btn_done": "✅ Done",
        "btn_back_menu": "🔙 Main Menu",
        # Available now
        "available_now_set": "🔥 You are now marked as available for the next 2 hours!",
        "available_now_list_header": "🔥 *Players available right now:*",
        "available_now_empty": "😔 No players available right now.",
        # Profile
        "profile_header": (
            "👤 *Your Profile*\n\n"
            "Name: {name}\n"
            "Level: {level}\n"
            "Level Source: {level_source}\n"
            "Area: {area}\n"
            "Courts: {courts}\n"
            "Matches: {matches}"
        ),
        "level_source_self_rated": "Self Rated",
        "level_source_coach_verified": "Coach Verified",
        "btn_edit_profile": "✏️ Edit Profile",
        "profile_incomplete": "⚠️ Profile incomplete. Starting onboarding...",
        # Settings
        "settings_header": "⚙️ *Settings* — what would you like to change?",
        "btn_change_language": "🌍 Language",
        "btn_change_area": "📍 Area",
        "btn_change_level": "📊 Level",
        "btn_change_courts": "🏟 Courts",
        "settings_saved": "✅ Settings updated!",
        # Misc
        "cancelled": "❌ Cancelled.",
        "error_generic": "⚠️ Something went wrong. Please try again.",
        "profile_not_complete_action": "⚠️ Please complete your profile first.",
        # Find Partner
        "partner_card_v2": (
            "👤 *{name}*\n\n"
            "🎾 NTRP {level}\n"
            "{level_source_line}\n\n"
            "📍 {area}\n\n"
            "🏟 {courts}"
        ),
        "level_source_card_self_rated": "✅ Self Rated",
        "level_source_card_coach_verified": "🏆 Coach Verified",
        "no_partners_friendly": (
            "🎾 We haven't found your ideal tennis partner yet.\n\n"
            "🌱 The Baseline community is growing every day.\n\n"
            "🎁 Invite a friend to Baseline — they might be your next opponent on the court."
        ),
        "btn_contact": "💬 Contact",
        "btn_next": "➡ Next",
        "btn_menu_home": "🏠 Menu",
        "no_contact_available": "This player has no public username yet. Try creating a game instead!",
    },
    "uk": {
        "welcome_new": "👋 Ласкаво просимо до *Baseline* — платформи пошуку партнерів для тенісу!\n\nДавайте налаштуємо ваш профіль.",
        "welcome_back": "👋 Ласкаво просимо, *{name}*!",
        "choose_language": "🌍 Оберіть мову:",
        "choose_level": "🎾 Оберіть ваш рівень (NTRP):",
        "choose_area": "📍 Оберіть домашній район:",
        "choose_courts": "🏟 Оберіть улюблені корти (натисніть для вибору, потім ✅ Готово):",
        "profile_complete": "✅ Профіль заповнено! Ласкаво просимо до Baseline.",
        "main_menu": "🎾 *Головне меню*\nЩо ви хочете зробити?",
        "btn_find_partner": "🎾 Знайти партнера",
        "btn_create_game": "📅 Створити гру",
        "btn_available_now": "🔥 Доступний зараз",
        "btn_my_profile": "👤 Мій профіль",
        "btn_settings": "⚙️ Налаштування",
        "finding_partners": "🔍 Шукаємо партнерів у *{area}* рівня *{level}* ±0.5...",
        "no_partners": (
            "🎾 Поки що ми не знайшли для вас ідеального партнера.\n\n"
            "🌱 Спільнота Baseline постійно зростає.\n\n"
            "🎁 Запросіть друга до Baseline — можливо, саме він стане вашим наступним суперником на корті."
        ),
        "partner_card": "👤 *{name}*\nРівень: {level}\nРайон: {area}\nРейтинг: {rating:.0f}",
        "btn_invite": "✉️ Запросити",
        "btn_view_profile": "👀 Профіль",
        "invite_sent": "✉️ Запрошення надіслано {name}!",
        "cg_enter_court": "🏟 *Крок 1/5* — Введіть назву або адресу корту:",
        "cg_enter_area": "📍 *Крок 2/5* — Оберіть район:",
        "cg_enter_date": "📅 *Крок 3/5* — Введіть дату (ДД.ММ.РРРР):",
        "cg_enter_time": "🕐 *Крок 4/5* — Введіть час (ГГ:ХХ):",
        "cg_choose_type": "🎾 *Крок 5а/5* — Одиночна чи парна?",
        "cg_choose_level": "📊 *Крок 5б/5* — Потрібний рівень (або пропустіть):",
        "cg_confirm": "✅ *Підтвердити гру*\n\n🏟 Корт: {court}\n📍 Район: {area}\n📅 Дата: {date}\n🕐 Час: {time}\n🎾 Тип: {match_type}\n📊 Рівень: {level}\n\nСтворити цю гру?",
        "cg_created": "🎉 Гру створено! ID: #{game_id}",
        "cg_error_date": "❌ Невірна дата. Використайте формат ДД.ММ.РРРР.",
        "cg_error_time": "❌ Невірний час. Використайте формат ГГ:ХХ.",
        "btn_singles": "1️⃣ Одиночна",
        "btn_doubles": "2️⃣ Парна",
        "btn_confirm": "✅ Підтвердити",
        "btn_cancel": "❌ Скасувати",
        "btn_skip": "⏭ Пропустити",
        "btn_done": "✅ Готово",
        "btn_back_menu": "🔙 Головне меню",
        "available_now_set": "🔥 Ви позначені як доступні на наступні 2 години!",
        "available_now_list_header": "🔥 *Гравці доступні зараз:*",
        "available_now_empty": "😔 Наразі немає доступних гравців.",
        "profile_header": "👤 *Ваш профіль*\n\nІм'я: {name}\nРівень: {level}\nДжерело рівня: {level_source}\nРайон: {area}\nКорти: {courts}\nМатчів: {matches}",
        "level_source_self_rated": "Самооцінка",
        "level_source_coach_verified": "Підтверджено тренером",
        "btn_edit_profile": "✏️ Редагувати профіль",
        "profile_incomplete": "⚠️ Профіль не заповнено. Починаємо реєстрацію...",
        "settings_header": "⚙️ *Налаштування* — що змінити?",
        "btn_change_language": "🌍 Мова",
        "btn_change_area": "📍 Район",
        "btn_change_level": "📊 Рівень",
        "btn_change_courts": "🏟 Корти",
        "settings_saved": "✅ Налаштування збережено!",
        "cancelled": "❌ Скасовано.",
        "error_generic": "⚠️ Щось пішло не так. Спробуйте ще раз.",
        "profile_not_complete_action": "⚠️ Будь ласка, спочатку заповніть профіль.",
        # Find Partner
        "partner_card_v2": (
            "👤 *{name}*\n\n"
            "🎾 NTRP {level}\n"
            "{level_source_line}\n\n"
            "📍 {area}\n\n"
            "🏟 {courts}"
        ),
        "level_source_card_self_rated": "✅ Самооцінка",
        "level_source_card_coach_verified": "🏆 Підтверджено тренером",
        "no_partners_friendly": (
            "🎾 Поки що ми не знайшли для вас ідеального партнера.\n\n"
            "🌱 Спільнота Baseline постійно зростає.\n\n"
            "🎁 Запросіть друга до Baseline — можливо, саме він стане вашим наступним суперником на корті."
        ),
        "btn_contact": "💬 Зв'язатися",
        "btn_next": "➡ Далі",
        "btn_menu_home": "🏠 Меню",
        "no_contact_available": "У цього гравця ще немає публічного username. Спробуйте створити гру!",
    },
    "ru": {
        "welcome_new": "👋 Добро пожаловать в *Baseline* — платформу поиска партнёров для тенниса!\n\nДавайте настроим ваш профиль.",
        "welcome_back": "👋 С возвращением, *{name}*!",
        "choose_language": "🌍 Выберите язык:",
        "choose_level": "🎾 Выберите ваш уровень (NTRP):",
        "choose_area": "📍 Выберите домашний район:",
        "choose_courts": "🏟 Выберите предпочитаемые корты (нажмите для выбора, затем ✅ Готово):",
        "profile_complete": "✅ Профиль заполнен! Добро пожаловать в Baseline.",
        "main_menu": "🎾 *Главное меню*\nЧто вы хотите сделать?",
        "btn_find_partner": "🎾 Найти партнёра",
        "btn_create_game": "📅 Создать игру",
        "btn_available_now": "🔥 Доступен сейчас",
        "btn_my_profile": "👤 Мой профиль",
        "btn_settings": "⚙️ Настройки",
        "finding_partners": "🔍 Ищем партнёров в *{area}* уровня *{level}* ±0.5...",
        "no_partners": (
            "🎾 Пока мы не нашли для вас идеального партнёра.\n\n"
            "🌱 Сообщество Baseline постоянно растёт.\n\n"
            "🎁 Пригласите друга в Baseline — возможно, именно он станет вашим следующим соперником на корте."
        ),
        "partner_card": "👤 *{name}*\nУровень: {level}\nРайон: {area}\nРейтинг: {rating:.0f}",
        "btn_invite": "✉️ Пригласить",
        "btn_view_profile": "👀 Профиль",
        "invite_sent": "✉️ Приглашение отправлено {name}!",
        "cg_enter_court": "🏟 *Шаг 1/5* — Введите название или адрес корта:",
        "cg_enter_area": "📍 *Шаг 2/5* — Выберите район:",
        "cg_enter_date": "📅 *Шаг 3/5* — Введите дату (ДД.ММ.ГГГГ):",
        "cg_enter_time": "🕐 *Шаг 4/5* — Введите время (ЧЧ:ММ):",
        "cg_choose_type": "🎾 *Шаг 5а/5* — Одиночная или парная?",
        "cg_choose_level": "📊 *Шаг 5б/5* — Нужный уровень (или пропустите):",
        "cg_confirm": "✅ *Подтвердить игру*\n\n🏟 Корт: {court}\n📍 Район: {area}\n📅 Дата: {date}\n🕐 Время: {time}\n🎾 Тип: {match_type}\n📊 Уровень: {level}\n\nСоздать эту игру?",
        "cg_created": "🎉 Игра создана! ID: #{game_id}",
        "cg_error_date": "❌ Неверная дата. Используйте формат ДД.ММ.ГГГГ.",
        "cg_error_time": "❌ Неверное время. Используйте формат ЧЧ:ММ.",
        "btn_singles": "1️⃣ Одиночная",
        "btn_doubles": "2️⃣ Парная",
        "btn_confirm": "✅ Подтвердить",
        "btn_cancel": "❌ Отмена",
        "btn_skip": "⏭ Пропустить",
        "btn_done": "✅ Готово",
        "btn_back_menu": "🔙 Главное меню",
        "available_now_set": "🔥 Вы отмечены как доступный на следующие 2 часа!",
        "available_now_list_header": "🔥 *Игроки доступны сейчас:*",
        "available_now_empty": "😔 Сейчас нет доступных игроков.",
        "profile_header": "👤 *Ваш профиль*\n\nИмя: {name}\nУровень: {level}\nИсточник уровня: {level_source}\nРайон: {area}\nКорты: {courts}\nМатчей: {matches}",
        "level_source_self_rated": "Самооценка",
        "level_source_coach_verified": "Подтверждено тренером",
        "btn_edit_profile": "✏️ Редактировать профиль",
        "profile_incomplete": "⚠️ Профиль не заполнен. Запускаем регистрацию...",
        "settings_header": "⚙️ *Настройки* — что изменить?",
        "btn_change_language": "🌍 Язык",
        "btn_change_area": "📍 Район",
        "btn_change_level": "📊 Уровень",
        "btn_change_courts": "🏟 Корты",
        "settings_saved": "✅ Настройки сохранены!",
        "cancelled": "❌ Отменено.",
        "error_generic": "⚠️ Что-то пошло не так. Попробуйте ещё раз.",
        "profile_not_complete_action": "⚠️ Пожалуйста, сначала заполните профиль.",
        # Find Partner
        "partner_card_v2": (
            "👤 *{name}*\n\n"
            "🎾 NTRP {level}\n"
            "{level_source_line}\n\n"
            "📍 {area}\n\n"
            "🏟 {courts}"
        ),
        "level_source_card_self_rated": "✅ Самооценка",
        "level_source_card_coach_verified": "🏆 Подтверждено тренером",
        "no_partners_friendly": (
            "🎾 Пока мы не нашли для вас идеального партнёра.\n\n"
            "🌱 Сообщество Baseline постоянно растёт.\n\n"
            "🎁 Пригласите друга в Baseline — возможно, именно он станет вашим следующим соперником на корте."
        ),
        "btn_contact": "💬 Связаться",
        "btn_next": "➡ Далее",
        "btn_menu_home": "🏠 Меню",
        "no_contact_available": "У этого игрока нет публичного username. Попробуйте создать игру!",
    },
}

DEFAULT_LANGUAGE: Language = "en"

AREAS = [
    "Downtown",
    "North York",
    "Etobicoke",
    "Mississauga",
    "Scarborough",
    "Richmond Hill",
    "Markham",
    "Other",
]

SKILL_LEVELS = ["2.5", "3.0", "3.5", "4.0", "4.5", "5.0"]

COURTS = [
    "Ramsden Park",
    "Eglinton Park",
    "Withrow Park",
    "Thomson Memorial Park",
    "Stanley Park",
    "High Park",
    "Rennie Park",
    "Other",
]


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Return a translated string for the given key and language.

    Falls back to English if the key or language is not found.
    """
    language = lang if lang in _TEXTS else DEFAULT_LANGUAGE
    text = _TEXTS[language].get(key) or _TEXTS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
