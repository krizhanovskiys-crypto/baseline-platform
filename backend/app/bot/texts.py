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
        "main_menu": "🏠 *Main Menu*\nWhat would you like to do?",
        "btn_find_partner": "🔍 Find Partner",
        "btn_available_now": "🔥 Available Now",
        "btn_my_profile": "👤 My Profile",
        "btn_settings": "⚙️ Settings",
        # Find partner
        "finding_partners": "🔍 Searching for partners in *{area}* at level *{level}* ±0.5...",
        "no_partners": (
            "😔 We haven't found your ideal tennis partner yet.\n\n"
            "🌱 The Baseline community is growing every day.\n\n"
            "🎁 Invite a friend to Baseline — they might be your next opponent on the court."
        ),
        "partner_card": "👤 *{name}*\nLevel: {level}\nArea: {area}",
        "btn_invite": "✉️ Invite",
        "btn_view_profile": "👀 View Profile",
        "invite_sent": "✉️ Invitation sent to {name}!",
        "btn_cancel": "❌ Cancel",
        "btn_done": "✅ Done",
        "btn_back_menu": "🏠 Main Menu",
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
        "btn_change_level": "🎾 Level",
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
            "😔 We haven't found your ideal tennis partner yet.\n\n"
            "🌱 The Baseline community is growing every day.\n\n"
            "🎁 Invite a friend to Baseline — they might be your next opponent on the court."
        ),
        "btn_contact": "💬 Contact",
        "btn_next": "➡️ Next",
        "btn_menu_home": "🏠 Menu",
        "no_contact_available": "This player has no public username yet. Try creating a game instead!",
        # Organize Match
        "btn_organize_match": "🎾 Organize Match",
        "om_choose_date": "📅 *Choose date*",
        "om_btn_today": "Today",
        "om_btn_tomorrow": "Tomorrow",
        "om_btn_other_date": "📅 Other Date",
        "om_enter_date": "Enter the date (DD.MM.YYYY):",
        "om_error_date": "❌ Invalid date. Use DD.MM.YYYY format.",
        "om_choose_time": "🕒 *Choose time*",
        "om_btn_other_time": "🕒 Other Time",
        "om_enter_time": "Enter the time (HH:MM):",
        "om_error_time": "❌ Invalid time. Use HH:MM format.",
        "om_choose_court": "📍 *Choose court*",
        "om_btn_other_court": "➕ Other Court",
        "om_enter_court": "Enter court name or address:",
        "om_choose_level": "🎾 *Skill Level*\n\nYour profile level: NTRP *{level}*",
        "om_btn_use_my_level": "✅ Use my level (NTRP {level})",
        "om_btn_change_level": "✏️ Change level",
        "om_choose_players": "👥 *Number of players*",
        "om_match_type_singles": "🎾 Singles",
        "om_match_type_doubles": "🎾 Doubles",
        "om_confirm": (
            "✅ *Confirm Match*\n\n"
            "📅 {date_label}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Level {level}\n"
            "{match_type}\n"
            "👥 {players} players\n\n"
            "Create match?"
        ),
        "om_btn_confirm": "✅ Create Match",
        "om_success": (
            "✅ *Match Created*\n\n"
            "📅 {date_label}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Level {level}\n"
            "{match_type}\n"
            "👥 1/{players} players"
        ),
        "om_btn_find_players": "🔍 Find Players",
        "om_btn_my_matches": "📋 My Matches",
        "om_my_matches_header": "📋 *Your Matches:*",
        # Find Players for Match
        "fpm_found": "👥 We found *{total}* suitable players",
        "fpm_browse_card": "{name}\n🎾 {level}\n📍 {area}",
        "fpm_not_found": (
            "👥 We couldn't find suitable players right now.\n\n"
            "The Baseline community is growing — new players will appear soon."
        ),
        "fpm_btn_select": "📨 Invite",
        "fpm_btn_prev": "⬅️ Previous",
        "fpm_btn_next": "➡️ Next",
        "fpm_selected_count": "✅ Invited: {count}",
        "fpm_btn_continue": "➕ Continue selecting",
        "fpm_btn_view_selected": "📋 Invited players",
        "fpm_selected_header": "*Invited players*",
        "fpm_selected_item": "• {name}",
        "fpm_btn_back": "⬅️ Back",
        # Invitations
        "inv_message": (
            "📨 *You have been invited to a match*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Level {level}\n"
            "👤 {organizer}"
        ),
        "inv_btn_accept": "✅ Accept",
        "inv_btn_decline": "❌ Decline",
        "inv_player_accepted": "✅ You joined the match! See you on the court.",
        "inv_player_declined": "❌ Invitation declined.",
        "inv_organizer_accepted": "✅ *{name}* accepted your invitation!",
        "inv_organizer_declined": "❌ *{name}* declined your invitation.",
        "inv_already_responded": "You have already responded to this invitation.",
        "inv_not_found": "Invitation not found.",
        "inv_not_yours": "This invitation is not for you.",
        "inv_duplicate": "Already invited.",
        # Game full notification (sent to organizer)
        "game_full_notification": "🎉 Your match is full!\n\nReview your roster before confirming.",
        "game_full_btn_confirm": "✅ Confirm Match",
        "game_full_btn_players": "👥 View Players",
        "game_full_btn_cancel": "❌ Cancel Match",
        # Confirm match flow
        "confirm_ask_note": (
            "Would you like to add a note for your players?\n\n"
            "For example: court number, parking, or what to bring.\n\n"
            "Max 200 characters. Tap *Skip* to confirm without a note."
        ),
        "confirm_btn_skip": "Skip",
        "confirm_note_too_long": "That note is too long ({length} chars). Please keep it under 200.",
        "confirm_match_done": "✅ Match confirmed! All players have been notified.",
        "confirm_match_not_yours": "Only the organizer can confirm this match.",
        "confirm_match_wrong_status": "This match cannot be confirmed right now.",
        # Player notification when match is CONFIRMED
        "confirmed_player_notification": (
            "🎉 *Your match is confirmed!*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n\n"
            "👥 *Players:*\n{players}"
        ),
        "confirmed_player_note_section": "\n\n*From the organizer:*\n{note}",
        # Cancel match
        "cancel_match_done": "❌ Match cancelled.",
        "cancel_match_not_yours": "Only the organizer can cancel this match.",
        "cancel_match_not_cancellable": "This match cannot be cancelled.",
        # View roster
        "view_roster_header": "👥 *Match Roster*\n\n📅 {date}\n🕒 {time}\n📍 {court}\n\n",
        "om_match_item": "📅 {date_label} • {time}\n📍 {court}\n👥 {players_joined}/{players_total}",
        "om_no_matches": "You haven't created any matches yet.",
        # Developer Mode
        "dev_menu_header": "🛠 *Developer Menu*",
        "dev_btn_create_players": "👥 Create Test Players",
        "dev_btn_reset_data": "🗑 Reset Test Data",
        "dev_btn_stats": "📊 Database Statistics",
        "dev_btn_exit": "🚪 Exit Developer Mode",
        "dev_players_created": "✅ Created {count} test player(s).",
        "dev_players_already_exist": "ℹ️ All test players already exist.",
        "dev_data_reset": "✅ Deleted {count} test player(s).",
        "dev_nothing_to_reset": "ℹ️ No test data found.",
        "dev_stats": (
            "📊 *Database Statistics*\n\n"
            "👥 Players: {players}\n"
            "✅ Complete profiles: {complete}\n"
            "📋 Games: {games}\n"
            "🔥 Available now: {available}"
        ),
    },
    "uk": {
        "welcome_new": "👋 Ласкаво просимо до *Baseline* — платформи пошуку партнерів для тенісу!\n\nДавайте налаштуємо ваш профіль.",
        "welcome_back": "👋 Ласкаво просимо, *{name}*!",
        "choose_language": "🌍 Оберіть мову:",
        "choose_level": "🎾 Оберіть ваш рівень (NTRP):",
        "choose_area": "📍 Оберіть домашній район:",
        "choose_courts": "🏟 Оберіть улюблені корти (натисніть для вибору, потім ✅ Готово):",
        "profile_complete": "✅ Профіль заповнено! Ласкаво просимо до Baseline.",
        "main_menu": "🏠 *Головне меню*\nЩо ви хочете зробити?",
        "btn_find_partner": "🔍 Знайти партнера",
        "btn_available_now": "🔥 Доступний зараз",
        "btn_my_profile": "👤 Мій профіль",
        "btn_settings": "⚙️ Налаштування",
        "finding_partners": "🔍 Шукаємо партнерів у *{area}* рівня *{level}* ±0.5...",
        "no_partners": (
            "😔 Поки що ми не знайшли для вас ідеального партнера.\n\n"
            "🌱 Спільнота Baseline постійно зростає.\n\n"
            "🎁 Запросіть друга до Baseline — можливо, саме він стане вашим наступним суперником на корті."
        ),
        "partner_card": "👤 *{name}*\nРівень: {level}\nРайон: {area}",
        "btn_invite": "✉️ Запросити",
        "btn_view_profile": "👀 Профіль",
        "invite_sent": "✉️ Запрошення надіслано {name}!",
        "btn_cancel": "❌ Скасувати",
        "btn_done": "✅ Готово",
        "btn_back_menu": "🏠 Головне меню",
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
        "btn_change_level": "🎾 Рівень",
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
            "😔 Поки що ми не знайшли для вас ідеального партнера.\n\n"
            "🌱 Спільнота Baseline постійно зростає.\n\n"
            "🎁 Запросіть друга до Baseline — можливо, саме він стане вашим наступним суперником на корті."
        ),
        "btn_contact": "💬 Зв'язатися",
        "btn_next": "➡️ Далі",
        "btn_menu_home": "🏠 Меню",
        "no_contact_available": "У цього гравця ще немає публічного username. Спробуйте створити гру!",
        # Organize Match
        "btn_organize_match": "🎾 Організувати матч",
        "om_choose_date": "📅 *Оберіть дату*",
        "om_btn_today": "Сьогодні",
        "om_btn_tomorrow": "Завтра",
        "om_btn_other_date": "📅 Інша дата",
        "om_enter_date": "Введіть дату (ДД.ММ.РРРР):",
        "om_error_date": "❌ Невірна дата. Використайте формат ДД.ММ.РРРР.",
        "om_choose_time": "🕒 *Оберіть час*",
        "om_btn_other_time": "🕒 Інший час",
        "om_enter_time": "Введіть час (ГГ:ХХ):",
        "om_error_time": "❌ Невірний час. Використайте формат ГГ:ХХ.",
        "om_choose_court": "📍 *Оберіть корт*",
        "om_btn_other_court": "➕ Інший корт",
        "om_enter_court": "Введіть назву або адресу корту:",
        "om_choose_level": "🎾 *Рівень гри*\n\nВаш рівень: NTRP *{level}*",
        "om_btn_use_my_level": "✅ Мій рівень (NTRP {level})",
        "om_btn_change_level": "✏️ Змінити рівень",
        "om_choose_players": "👥 *Кількість гравців*",
        "om_match_type_singles": "🎾 Одиночний матч",
        "om_match_type_doubles": "🎾 Парний матч",
        "om_confirm": (
            "✅ *Підтвердити матч*\n\n"
            "📅 {date_label}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Рівень {level}\n"
            "{match_type}\n"
            "👥 {players} гравців\n\n"
            "Створити матч?"
        ),
        "om_btn_confirm": "✅ Створити матч",
        "om_success": (
            "✅ *Матч створено*\n\n"
            "📅 {date_label}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Рівень {level}\n"
            "{match_type}\n"
            "👥 1/{players} гравців"
        ),
        "om_btn_find_players": "🔍 Знайти гравців",
        "om_btn_my_matches": "📋 Мої матчі",
        "om_my_matches_header": "📋 *Ваші матчі:*",
        # Find Players for Match
        "fpm_found": "👥 Ми знайшли *{total}* гравців для вашого матчу",
        "fpm_browse_card": "{name}\n🎾 {level}\n📍 {area}",
        "fpm_not_found": (
            "👥 Наразі ми не знайшли підходящих гравців.\n\n"
            "Спільнота Baseline постійно зростає — нові гравці з'являться незабаром."
        ),
        "fpm_btn_select": "📨 Запросити",
        "fpm_btn_prev": "⬅️ Попередній",
        "fpm_btn_next": "➡️ Наступний",
        "fpm_selected_count": "✅ Запрошено: {count}",
        "fpm_btn_continue": "➕ Продовжити вибір",
        "fpm_btn_view_selected": "📋 Запрошені гравці",
        "fpm_selected_header": "*Запрошені гравці*",
        "fpm_selected_item": "• {name}",
        "fpm_btn_back": "⬅️ Назад",
        # Invitations
        "inv_message": (
            "📨 *Вас запрошено на матч*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Рівень {level}\n"
            "👤 {organizer}"
        ),
        "inv_btn_accept": "✅ Прийняти",
        "inv_btn_decline": "❌ Відхилити",
        "inv_player_accepted": "✅ Ви приєдналися до матчу! До зустрічі на корті.",
        "inv_player_declined": "❌ Запрошення відхилено.",
        "inv_organizer_accepted": "✅ *{name}* прийняв ваше запрошення!",
        "inv_organizer_declined": "❌ *{name}* відхилив ваше запрошення.",
        "inv_already_responded": "Ви вже відповіли на це запрошення.",
        "inv_not_found": "Запрошення не знайдено.",
        "inv_not_yours": "Це запрошення не для вас.",
        "inv_duplicate": "Вже запрошено.",
        # Game full notification (sent to organizer)
        "game_full_notification": "🎉 Ваш матч укомплектований!\n\nПеревірте склад перед підтвердженням.",
        "game_full_btn_confirm": "✅ Підтвердити матч",
        "game_full_btn_players": "👥 Переглянути гравців",
        "game_full_btn_cancel": "❌ Скасувати матч",
        # Confirm match flow
        "confirm_ask_note": (
            "Хочете додати повідомлення для гравців?\n\n"
            "Наприклад: номер корту, парковка або що взяти з собою.\n\n"
            "Максимум 200 символів. Натисніть *Пропустити*, щоб підтвердити без повідомлення."
        ),
        "confirm_btn_skip": "Пропустити",
        "confirm_note_too_long": "Повідомлення занадто довге ({length} символів). Будь ласка, скоротіть до 200.",
        "confirm_match_done": "✅ Матч підтверджено! Усіх гравців повідомлено.",
        "confirm_match_not_yours": "Тільки організатор може підтвердити матч.",
        "confirm_match_wrong_status": "Цей матч зараз не можна підтвердити.",
        # Player notification when match is CONFIRMED
        "confirmed_player_notification": (
            "🎉 *Ваш матч підтверджено!*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n\n"
            "👥 *Гравці:*\n{players}"
        ),
        "confirmed_player_note_section": "\n\n*Від організатора:*\n{note}",
        # Cancel match
        "cancel_match_done": "❌ Матч скасовано.",
        "cancel_match_not_yours": "Тільки організатор може скасувати матч.",
        "cancel_match_not_cancellable": "Цей матч не можна скасувати.",
        # View roster
        "view_roster_header": "👥 *Склад матчу*\n\n📅 {date}\n🕒 {time}\n📍 {court}\n\n",
        "om_match_item": "📅 {date_label} • {time}\n📍 {court}\n👥 {players_joined}/{players_total}",
        "om_no_matches": "Ви ще не створили жодного матчу.",
        # Developer Mode
        "dev_menu_header": "🛠 *Меню розробника*",
        "dev_btn_create_players": "👥 Створити тестових гравців",
        "dev_btn_reset_data": "🗑 Скинути тестові дані",
        "dev_btn_stats": "📊 Статистика бази даних",
        "dev_btn_exit": "🚪 Вийти з режиму розробника",
        "dev_players_created": "✅ Створено {count} тестовий(-их) гравець(-ів).",
        "dev_players_already_exist": "ℹ️ Усі тестові гравці вже існують.",
        "dev_data_reset": "✅ Видалено {count} тестовий(-их) гравець(-ів).",
        "dev_nothing_to_reset": "ℹ️ Тестових даних не знайдено.",
        "dev_stats": (
            "📊 *Статистика бази даних*\n\n"
            "👥 Гравці: {players}\n"
            "✅ Повні профілі: {complete}\n"
            "📋 Ігри: {games}\n"
            "🔥 Доступні зараз: {available}"
        ),
    },
    "ru": {
        "welcome_new": "👋 Добро пожаловать в *Baseline* — платформу поиска партнёров для тенниса!\n\nДавайте настроим ваш профиль.",
        "welcome_back": "👋 С возвращением, *{name}*!",
        "choose_language": "🌍 Выберите язык:",
        "choose_level": "🎾 Выберите ваш уровень (NTRP):",
        "choose_area": "📍 Выберите домашний район:",
        "choose_courts": "🏟 Выберите предпочитаемые корты (нажмите для выбора, затем ✅ Готово):",
        "profile_complete": "✅ Профиль заполнен! Добро пожаловать в Baseline.",
        "main_menu": "🏠 *Главное меню*\nЧто вы хотите сделать?",
        "btn_find_partner": "🔍 Найти партнёра",
        "btn_available_now": "🔥 Доступен сейчас",
        "btn_my_profile": "👤 Мой профиль",
        "btn_settings": "⚙️ Настройки",
        "finding_partners": "🔍 Ищем партнёров в *{area}* уровня *{level}* ±0.5...",
        "no_partners": (
            "😔 Пока мы не нашли для вас идеального партнёра.\n\n"
            "🌱 Сообщество Baseline постоянно растёт.\n\n"
            "🎁 Пригласите друга в Baseline — возможно, именно он станет вашим следующим соперником на корте."
        ),
        "partner_card": "👤 *{name}*\nУровень: {level}\nРайон: {area}",
        "btn_invite": "✉️ Пригласить",
        "btn_view_profile": "👀 Профиль",
        "invite_sent": "✉️ Приглашение отправлено {name}!",
        "btn_cancel": "❌ Отмена",
        "btn_done": "✅ Готово",
        "btn_back_menu": "🏠 Главное меню",
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
        "btn_change_level": "🎾 Уровень",
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
            "😔 Пока мы не нашли для вас идеального партнёра.\n\n"
            "🌱 Сообщество Baseline постоянно растёт.\n\n"
            "🎁 Пригласите друга в Baseline — возможно, именно он станет вашим следующим соперником на корте."
        ),
        "btn_contact": "💬 Связаться",
        "btn_next": "➡️ Далее",
        "btn_menu_home": "🏠 Меню",
        "no_contact_available": "У этого игрока нет публичного username. Попробуйте создать игру!",
        # Organize Match
        "btn_organize_match": "🎾 Организовать матч",
        "om_choose_date": "📅 *Выберите дату*",
        "om_btn_today": "Сегодня",
        "om_btn_tomorrow": "Завтра",
        "om_btn_other_date": "📅 Другая дата",
        "om_enter_date": "Введите дату (ДД.ММ.ГГГГ):",
        "om_error_date": "❌ Неверная дата. Используйте формат ДД.ММ.ГГГГ.",
        "om_choose_time": "🕒 *Выберите время*",
        "om_btn_other_time": "🕒 Другое время",
        "om_enter_time": "Введите время (ЧЧ:ММ):",
        "om_error_time": "❌ Неверное время. Используйте формат ЧЧ:ММ.",
        "om_choose_court": "📍 *Выберите корт*",
        "om_btn_other_court": "➕ Другой корт",
        "om_enter_court": "Введите название или адрес корта:",
        "om_choose_level": "🎾 *Уровень игры*\n\nВаш уровень: NTRP *{level}*",
        "om_btn_use_my_level": "✅ Мой уровень (NTRP {level})",
        "om_btn_change_level": "✏️ Изменить уровень",
        "om_choose_players": "👥 *Количество игроков*",
        "om_match_type_singles": "🎾 Одиночный матч",
        "om_match_type_doubles": "🎾 Парный матч",
        "om_confirm": (
            "✅ *Подтвердить матч*\n\n"
            "📅 {date_label}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Уровень {level}\n"
            "{match_type}\n"
            "👥 {players} игроков\n\n"
            "Создать матч?"
        ),
        "om_btn_confirm": "✅ Создать матч",
        "om_success": (
            "✅ *Матч создан*\n\n"
            "📅 {date_label}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Уровень {level}\n"
            "{match_type}\n"
            "👥 1/{players} игроков"
        ),
        "om_btn_find_players": "🔍 Найти игроков",
        "om_btn_my_matches": "📋 Мои матчи",
        "om_my_matches_header": "📋 *Ваши матчи:*",
        # Find Players for Match
        "fpm_found": "👥 Мы нашли *{total}* игроков для вашего матча",
        "fpm_browse_card": "{name}\n🎾 {level}\n📍 {area}",
        "fpm_not_found": (
            "👥 Сейчас мы не нашли подходящих игроков.\n\n"
            "Сообщество Baseline постоянно растёт — новые игроки появятся совсем скоро."
        ),
        "fpm_btn_select": "📨 Пригласить",
        "fpm_btn_prev": "⬅️ Предыдущий",
        "fpm_btn_next": "➡️ Следующий",
        "fpm_selected_count": "✅ Приглашено: {count}",
        "fpm_btn_continue": "➕ Продолжить выбор",
        "fpm_btn_view_selected": "📋 Приглашённые игроки",
        "fpm_selected_header": "*Приглашённые игроки*",
        "fpm_selected_item": "• {name}",
        "fpm_btn_back": "⬅️ Назад",
        # Invitations
        "inv_message": (
            "📨 *Вас приглашают на матч*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "🎾 Уровень {level}\n"
            "👤 {organizer}"
        ),
        "inv_btn_accept": "✅ Принять",
        "inv_btn_decline": "❌ Отклонить",
        "inv_player_accepted": "✅ Вы присоединились к матчу! Увидимся на корте.",
        "inv_player_declined": "❌ Приглашение отклонено.",
        "inv_organizer_accepted": "✅ *{name}* принял ваше приглашение!",
        "inv_organizer_declined": "❌ *{name}* отклонил ваше приглашение.",
        "inv_already_responded": "Вы уже ответили на это приглашение.",
        "inv_not_found": "Приглашение не найдено.",
        "inv_not_yours": "Это приглашение не для вас.",
        "inv_duplicate": "Уже приглашён.",
        # Game full notification (sent to organizer)
        "game_full_notification": "🎉 Ваш матч укомплектован!\n\nПроверьте состав перед подтверждением.",
        "game_full_btn_confirm": "✅ Подтвердить матч",
        "game_full_btn_players": "👥 Просмотреть игроков",
        "game_full_btn_cancel": "❌ Отменить матч",
        # Confirm match flow
        "confirm_ask_note": (
            "Хотите добавить сообщение для игроков?\n\n"
            "Например: номер корта, парковка или что взять с собой.\n\n"
            "Максимум 200 символов. Нажмите *Пропустить*, чтобы подтвердить без сообщения."
        ),
        "confirm_btn_skip": "Пропустить",
        "confirm_note_too_long": "Сообщение слишком длинное ({length} символов). Пожалуйста, сократите до 200.",
        "confirm_match_done": "✅ Матч подтверждён! Все игроки уведомлены.",
        "confirm_match_not_yours": "Только организатор может подтвердить матч.",
        "confirm_match_wrong_status": "Этот матч сейчас нельзя подтвердить.",
        # Player notification when match is CONFIRMED
        "confirmed_player_notification": (
            "🎉 *Ваш матч подтверждён!*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n\n"
            "👥 *Игроки:*\n{players}"
        ),
        "confirmed_player_note_section": "\n\n*От организатора:*\n{note}",
        # Cancel match
        "cancel_match_done": "❌ Матч отменён.",
        "cancel_match_not_yours": "Только организатор может отменить матч.",
        "cancel_match_not_cancellable": "Этот матч нельзя отменить.",
        # View roster
        "view_roster_header": "👥 *Состав матча*\n\n📅 {date}\n🕒 {time}\n📍 {court}\n\n",
        "om_match_item": "📅 {date_label} • {time}\n📍 {court}\n👥 {players_joined}/{players_total}",
        "om_no_matches": "Вы ещё не создали ни одного матча.",
        # Developer Mode
        "dev_menu_header": "🛠 *Меню разработчика*",
        "dev_btn_create_players": "👥 Создать тестовых игроков",
        "dev_btn_reset_data": "🗑 Сбросить тестовые данные",
        "dev_btn_stats": "📊 Статистика базы данных",
        "dev_btn_exit": "🚪 Выйти из режима разработчика",
        "dev_players_created": "✅ Создано {count} тестовый(-ых) игрок(-ов).",
        "dev_players_already_exist": "ℹ️ Все тестовые игроки уже существуют.",
        "dev_data_reset": "✅ Удалено {count} тестовый(-ых) игрок(-ов).",
        "dev_nothing_to_reset": "ℹ️ Тестовые данные не найдены.",
        "dev_stats": (
            "📊 *Статистика базы данных*\n\n"
            "👥 Игроки: {players}\n"
            "✅ Полные профили: {complete}\n"
            "📋 Игры: {games}\n"
            "🔥 Доступны сейчас: {available}"
        ),
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
