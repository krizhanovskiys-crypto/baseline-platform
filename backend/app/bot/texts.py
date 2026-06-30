"""UI text strings for the Telegram bot, keyed by language code."""
from typing import Literal

Language = Literal["en", "uk", "ru"]

_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        # Onboarding
        "welcome_new": "👋 Welcome to *Baseline* — the tennis matchmaking platform!\n\nLet's set up your profile.",
        "welcome_back": "👋 Welcome back, *{name}*!",
        "choose_language": "🌍 Choose your language:",
        "choose_level": "📊 Choose your skill level (NTRP):",
        "choose_area": "📍 Choose your home area:",
        "choose_courts": "🏟 Select your preferred courts (tap to toggle, then tap ✅ Done):",
        "profile_complete": "✅ Profile complete! Welcome to Baseline.",
        # Main menu
        "main_menu": "🏠 *Main Menu*\nWhat would you like to do?",
        "btn_find_partner": "🔍 Find Partner",
        "btn_available_now": "🔥 Available Now",
        "btn_my_matches": "📋 My Matches",
        "btn_my_profile": "👤 My Profile",
        "btn_settings": "⚙️ Settings",
        # My Matches
        "my_matches_header": "📋 *My Matches*",
        "my_matches_empty": (
            "😔 You have no upcoming matches yet.\n\n"
            "Organize a match or accept an invitation to see it here."
        ),
        "my_matches_card": (
            "{match_type}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {court}\n"
            "👥 {players_joined}/{players_total}\n"
            "{status}"
        ),
        "my_matches_btn_open": "Open Match",
        "match_details_card": (
            "📋 *Match Details*\n\n"
            "{match_type}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {area} • 🏟 {court}\n"
            "📊 Level {level}\n"
            "{status}\n\n"
            "👑 Host\n{organizer}\n\n"
            "👥 Players ({count}/{total}):\n{players}\n\n"
            "{slots_line}"
        ),
        "match_details_btn_back": "⬅️ My Matches",
        "match_details_btn_add_player": "➕ Add Player",
        "match_details_btn_cancel_match": "❌ Cancel Match",
        "match_details_btn_leave_match": "Leave Match",
        "match_details_btn_join_match": "Join Match",
        "match_details_1_player_needed": "➕ 1 player needed",
        "match_details_players_needed": "➕ {n} players needed",
        "feature_not_yet": "⚠️ Coming soon.",
        "match_not_found": "⚠️ Match not found.",
        "status_open": "Looking for players",
        "status_partially_filled": "Filling up",
        "status_full": "Full",
        "status_confirmed": "Confirmed ✅",
        "status_badge_open": "🟢 Looking for players",
        "status_badge_partially_filled": "🟡 Filling up",
        "status_badge_full": "🔵 Full",
        "status_badge_confirmed": "🔵 Confirmed",
        "status_badge_cancelled": "🔴 Cancelled",
        "status_badge_expired": "🔴 Expired",
        # Available Matches
        "btn_available_matches": "🎾 Available Matches",
        "available_matches_header": "🎾 *Available Matches*\n{count} matches found",
        "available_matches_empty": (
            "😔 No matches available right now.\n\n"
            "Organize one yourself, or check back later."
        ),
        "available_matches_card": (
            "{match_type}\n"
            "📊 Level {level}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {area} • 🏟 {court}\n"
            "👥 {players_joined}/{players_total}\n"
            "{status}"
        ),
        "available_matches_btn_view_details": "View Details",
        "available_matches_btn_filters": "Filters",
        "available_matches_btn_prev": "⬅️ Previous",
        "available_matches_btn_next": "➡️ Next",
        "available_matches_filters_header": "*Filters*",
        "available_matches_filter_area": "📍 Area",
        "available_matches_filter_date": "📅 Date",
        "available_matches_filter_level": "⭐ Level",
        "available_matches_filter_match_type": "🎾 Match Type",
        "available_matches_filter_any": "Any",
        "available_matches_btn_apply": "✅ Apply",
        "available_matches_page_indicator": "Page {page}/{total_pages}",
        "join_confirm_text": "Join this match?\n\nThe host will be notified.",
        "join_confirm_btn_join": "✅ Join",
        "join_confirm_btn_cancel": "❌ Cancel",
        "join_success_text": (
            "✅ Successfully joined.\n\n"
            "The host has been notified.\n\n"
            "You can find this match in My Matches."
        ),
        "join_match_notification": "👤 {name} joined your match.",
        "join_match_not_allowed": "⚠️ This match can no longer be joined.",
        "join_match_organizer": "⚠️ You can't join your own match.",
        "join_match_already_joined": "⚠️ You already joined this match.",
        "match_already_full": "😔 This match just became full.",
        # Find partner
        "finding_partners": "🔍 Searching for partners in *{area}* at level *{level}* ±0.5...",
        "no_partners": (
            "😔 We haven't found your ideal tennis partner yet.\n\n"
            "🌱 The Baseline community is growing every day.\n\n"
            "🎁 Invite a friend to Baseline — they might be your next opponent on the court."
        ),
        "partner_card": "👤 *{name}*\nLevel: {level}\nArea: {area}",
        "btn_invite": "📨 Invite",
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
            "👤 Name: {name}\n"
            "⭐ Level: {level}\n"
            "📖 Level Source: {level_source}\n"
            "📍 Area: {area}\n"
            "🎾 Courts: {courts}\n"
            "📊 Matches: {matches}"
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
            "📊 NTRP {level}\n"
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
        "om_choose_level": "📊 *Skill Level*\n\nYour profile level: NTRP *{level}*",
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
            "📊 Level {level}\n"
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
            "📊 Level {level}\n"
            "{match_type}\n"
            "👥 1/{players} players"
        ),
        "om_btn_find_players": "🔍 Find Players",
        "om_btn_my_matches": "📋 My Matches",
        "om_my_matches_header": "📋 *Your Matches:*",
        # Find Players for Match
        "fpm_found": "👥 We found *{total}* suitable players",
        "fpm_browse_card": "{name}\n📊 {level}\n📍 {area}",
        "fpm_not_found": (
            "😔 We couldn't find suitable players right now.\n\n"
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
            "📊 Level {level}\n"
            "👤 {organizer}"
        ),
        "inv_message_singles": (
            "🎾 *You have been invited to a singles match.*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "📊 Level {level}\n"
            "👤 {organizer}"
        ),
        "inv_message_doubles": (
            "🎾 *You have been invited to a doubles match.*\n"
            "We are still looking for more players.\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "📊 Level {level}\n"
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
        "inv_game_expired": "⚠️ This match has already expired and can no longer be joined.",
        "inv_duplicate": "Already invited.",
        "inv_delivery_failed": "⚠ Unfortunately, we couldn't send the invitation to this player.",
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
        # Leave match
        "leave_match_done": "✅ You left the match.",
        "leave_match_organizer": "⚠️ Organizer cannot leave. Use Cancel Match instead.",
        "leave_match_not_participant": "⚠️ You are not a participant in this match.",
        "leave_match_not_allowed": "⚠️ You cannot leave a match at this stage.",
        "leave_match_notification": "👤 {name} left your match.",
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
        "choose_level": "📊 Оберіть ваш рівень (NTRP):",
        "choose_area": "📍 Оберіть домашній район:",
        "choose_courts": "🏟 Оберіть улюблені корти (натисніть для вибору, потім ✅ Готово):",
        "profile_complete": "✅ Профіль заповнено! Ласкаво просимо до Baseline.",
        "main_menu": "🏠 *Головне меню*\nЩо ви хочете зробити?",
        "btn_find_partner": "🔍 Знайти партнера",
        "btn_available_now": "🔥 Доступний зараз",
        "btn_my_matches": "📋 Мої матчі",
        "btn_my_profile": "👤 Мій профіль",
        "btn_settings": "⚙️ Налаштування",
        # My Matches
        "my_matches_header": "📋 *Мої матчі*",
        "my_matches_empty": (
            "😔 Поки що у вас немає майбутніх матчів.\n\n"
            "Організуйте матч або прийміть запрошення, щоб побачити його тут."
        ),
        "my_matches_card": (
            "{match_type}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {court}\n"
            "👥 {players_joined}/{players_total}\n"
            "{status}"
        ),
        "my_matches_btn_open": "Відкрити матч",
        "match_details_card": (
            "📋 *Деталі матчу*\n\n"
            "{match_type}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {area} • 🏟 {court}\n"
            "📊 Рівень {level}\n"
            "{status}\n\n"
            "👑 Господар\n{organizer}\n\n"
            "👥 Гравці ({count}/{total}):\n{players}\n\n"
            "{slots_line}"
        ),
        "match_details_btn_back": "⬅️ Мої матчі",
        "match_details_btn_add_player": "➕ Додати гравця",
        "match_details_btn_cancel_match": "❌ Скасувати матч",
        "match_details_btn_leave_match": "Покинути матч",
        "match_details_btn_join_match": "Приєднатися",
        "match_details_1_player_needed": "➕ Потрібен 1 гравець",
        "match_details_players_needed": "➕ Потрібно {n} гравців",
        "feature_not_yet": "⚠️ Незабаром.",
        "match_not_found": "⚠️ Матч не знайдено.",
        "status_open": "Шукаємо гравців",
        "status_partially_filled": "Набираємо команду",
        "status_full": "Команда зібрана",
        "status_confirmed": "Підтверджено ✅",
        "status_badge_open": "🟢 Шукаємо гравців",
        "status_badge_partially_filled": "🟡 Набираємо команду",
        "status_badge_full": "🔵 Команда зібрана",
        "status_badge_confirmed": "🔵 Підтверджено",
        "status_badge_cancelled": "🔴 Скасовано",
        "status_badge_expired": "🔴 Завершено",
        # Available Matches
        "btn_available_matches": "🎾 Доступні матчі",
        "available_matches_header": "🎾 *Доступні матчі*\n{count} матчів знайдено",
        "available_matches_empty": (
            "😔 Зараз немає доступних матчів.\n\n"
            "Організуйте свій матч або перевірте пізніше."
        ),
        "available_matches_card": (
            "{match_type}\n"
            "📊 Рівень {level}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {area} • 🏟 {court}\n"
            "👥 {players_joined}/{players_total}\n"
            "{status}"
        ),
        "available_matches_btn_view_details": "Детальніше",
        "available_matches_btn_filters": "Фільтри",
        "available_matches_btn_prev": "⬅️ Попередня",
        "available_matches_btn_next": "➡️ Наступна",
        "available_matches_filters_header": "*Фільтри*",
        "available_matches_filter_area": "📍 Район",
        "available_matches_filter_date": "📅 Дата",
        "available_matches_filter_level": "⭐ Рівень",
        "available_matches_filter_match_type": "🎾 Тип матчу",
        "available_matches_filter_any": "Будь-який",
        "available_matches_btn_apply": "✅ Застосувати",
        "available_matches_page_indicator": "Сторінка {page}/{total_pages}",
        "join_confirm_text": "Приєднатися до цього матчу?\n\nГосподаря буде повідомлено.",
        "join_confirm_btn_join": "✅ Приєднатися",
        "join_confirm_btn_cancel": "❌ Скасувати",
        "join_success_text": (
            "✅ Ви успішно приєдналися.\n\n"
            "Господаря повідомлено.\n\n"
            "Цей матч можна знайти в розділі «Мої матчі»."
        ),
        "join_match_notification": "👤 {name} приєднався(-лася) до вашого матчу.",
        "join_match_not_allowed": "⚠️ До цього матчу більше не можна приєднатися.",
        "join_match_organizer": "⚠️ Ви не можете приєднатися до власного матчу.",
        "join_match_already_joined": "⚠️ Ви вже приєдналися до цього матчу.",
        "match_already_full": "😔 Цей матч щойно заповнився.",
        "finding_partners": "🔍 Шукаємо партнерів у *{area}* рівня *{level}* ±0.5...",
        "no_partners": (
            "😔 Поки що ми не знайшли для вас ідеального партнера.\n\n"
            "🌱 Спільнота Baseline постійно зростає.\n\n"
            "🎁 Запросіть друга до Baseline — можливо, саме він стане вашим наступним суперником на корті."
        ),
        "partner_card": "👤 *{name}*\nРівень: {level}\nРайон: {area}",
        "btn_invite": "📨 Запросити",
        "btn_view_profile": "👀 Профіль",
        "invite_sent": "✉️ Запрошення надіслано {name}!",
        "btn_cancel": "❌ Скасувати",
        "btn_done": "✅ Готово",
        "btn_back_menu": "🏠 Головне меню",
        "available_now_set": "🔥 Ви позначені як доступні на наступні 2 години!",
        "available_now_list_header": "🔥 *Гравці доступні зараз:*",
        "available_now_empty": "😔 Наразі немає доступних гравців.",
        "profile_header": "👤 *Ваш профіль*\n\n👤 Ім'я: {name}\n⭐ Рівень: {level}\n📖 Джерело рівня: {level_source}\n📍 Район: {area}\n🎾 Корти: {courts}\n📊 Матчів: {matches}",
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
            "📊 NTRP {level}\n"
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
        "om_choose_level": "📊 *Рівень гри*\n\nВаш рівень: NTRP *{level}*",
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
            "📊 Рівень {level}\n"
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
            "📊 Рівень {level}\n"
            "{match_type}\n"
            "👥 1/{players} гравців"
        ),
        "om_btn_find_players": "🔍 Знайти гравців",
        "om_btn_my_matches": "📋 Мої матчі",
        "om_my_matches_header": "📋 *Ваші матчі:*",
        # Find Players for Match
        "fpm_found": "👥 Ми знайшли *{total}* гравців для вашого матчу",
        "fpm_browse_card": "{name}\n📊 {level}\n📍 {area}",
        "fpm_not_found": (
            "😔 Наразі ми не знайшли підходящих гравців.\n\n"
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
            "📊 Рівень {level}\n"
            "👤 {organizer}"
        ),
        "inv_message_singles": (
            "🎾 *Вас запрошено на одиночний матч.*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "📊 Рівень {level}\n"
            "👤 {organizer}"
        ),
        "inv_message_doubles": (
            "🎾 *Вас запрошено на парний матч.*\n"
            "Ми ще шукаємо гравців.\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "📊 Рівень {level}\n"
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
        "inv_game_expired": "⚠️ Цей матч вже завершився і більше не приймає учасників.",
        "inv_duplicate": "Вже запрошено.",
        "inv_delivery_failed": "⚠ На жаль, ми не змогли надіслати запрошення цьому гравцю.",
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
        # Leave match
        "leave_match_done": "✅ Ви покинули матч.",
        "leave_match_organizer": "⚠️ Господар не може покинути матч. Скористайтесь скасуванням.",
        "leave_match_not_participant": "⚠️ Ви не є учасником цього матчу.",
        "leave_match_not_allowed": "⚠️ На цьому етапі покинути матч неможливо.",
        "leave_match_notification": "👤 {name} покинув(-ла) ваш матч.",
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
        "choose_level": "📊 Выберите ваш уровень (NTRP):",
        "choose_area": "📍 Выберите домашний район:",
        "choose_courts": "🏟 Выберите предпочитаемые корты (нажмите для выбора, затем ✅ Готово):",
        "profile_complete": "✅ Профиль заполнен! Добро пожаловать в Baseline.",
        "main_menu": "🏠 *Главное меню*\nЧто вы хотите сделать?",
        "btn_find_partner": "🔍 Найти партнёра",
        "btn_available_now": "🔥 Доступен сейчас",
        "btn_my_matches": "📋 Мои матчи",
        "btn_my_profile": "👤 Мой профиль",
        "btn_settings": "⚙️ Настройки",
        # My Matches
        "my_matches_header": "📋 *Мои матчи*",
        "my_matches_empty": (
            "😔 У вас пока нет предстоящих матчей.\n\n"
            "Организуйте матч или примите приглашение, чтобы увидеть его здесь."
        ),
        "my_matches_card": (
            "{match_type}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {court}\n"
            "👥 {players_joined}/{players_total}\n"
            "{status}"
        ),
        "my_matches_btn_open": "Открыть матч",
        "match_details_card": (
            "📋 *Детали матча*\n\n"
            "{match_type}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {area} • 🏟 {court}\n"
            "📊 Уровень {level}\n"
            "{status}\n\n"
            "👑 Хозяин\n{organizer}\n\n"
            "👥 Игроки ({count}/{total}):\n{players}\n\n"
            "{slots_line}"
        ),
        "match_details_btn_back": "⬅️ Мои матчи",
        "match_details_btn_add_player": "➕ Добавить игрока",
        "match_details_btn_cancel_match": "❌ Отменить матч",
        "match_details_btn_leave_match": "Покинуть матч",
        "match_details_btn_join_match": "Присоединиться",
        "match_details_1_player_needed": "➕ Нужен 1 игрок",
        "match_details_players_needed": "➕ Нужно {n} игроков",
        "feature_not_yet": "⚠️ Скоро.",
        "match_not_found": "⚠️ Матч не найден.",
        "status_open": "Набираем игроков",
        "status_partially_filled": "Набираем команду",
        "status_full": "Команда собрана",
        "status_confirmed": "Подтверждено ✅",
        "status_badge_open": "🟢 Набираем игроков",
        "status_badge_partially_filled": "🟡 Набираем команду",
        "status_badge_full": "🔵 Команда собрана",
        "status_badge_confirmed": "🔵 Подтверждено",
        "status_badge_cancelled": "🔴 Отменён",
        "status_badge_expired": "🔴 Завершён",
        # Available Matches
        "btn_available_matches": "🎾 Доступные матчи",
        "available_matches_header": "🎾 *Доступные матчи*\n{count} матчей найдено",
        "available_matches_empty": (
            "😔 Сейчас нет доступных матчей.\n\n"
            "Организуйте свой матч или проверьте позже."
        ),
        "available_matches_card": (
            "{match_type}\n"
            "📊 Уровень {level}\n"
            "📅 {date} • 🕒 {time}\n"
            "📍 {area} • 🏟 {court}\n"
            "👥 {players_joined}/{players_total}\n"
            "{status}"
        ),
        "available_matches_btn_view_details": "Подробнее",
        "available_matches_btn_filters": "Фильтры",
        "available_matches_btn_prev": "⬅️ Предыдущая",
        "available_matches_btn_next": "➡️ Следующая",
        "available_matches_filters_header": "*Фильтры*",
        "available_matches_filter_area": "📍 Район",
        "available_matches_filter_date": "📅 Дата",
        "available_matches_filter_level": "⭐ Уровень",
        "available_matches_filter_match_type": "🎾 Тип матча",
        "available_matches_filter_any": "Любой",
        "available_matches_btn_apply": "✅ Применить",
        "available_matches_page_indicator": "Страница {page}/{total_pages}",
        "join_confirm_text": "Присоединиться к этому матчу?\n\nХозяин будет уведомлён.",
        "join_confirm_btn_join": "✅ Присоединиться",
        "join_confirm_btn_cancel": "❌ Отмена",
        "join_success_text": (
            "✅ Вы успешно присоединились.\n\n"
            "Хозяин уведомлён.\n\n"
            "Этот матч можно найти в разделе «Мои матчи»."
        ),
        "join_match_notification": "👤 {name} присоединился(-ась) к вашему матчу.",
        "join_match_not_allowed": "⚠️ К этому матчу больше нельзя присоединиться.",
        "join_match_organizer": "⚠️ Вы не можете присоединиться к собственному матчу.",
        "join_match_already_joined": "⚠️ Вы уже присоединились к этому матчу.",
        "match_already_full": "😔 Этот матч только что заполнился.",
        "finding_partners": "🔍 Ищем партнёров в *{area}* уровня *{level}* ±0.5...",
        "no_partners": (
            "😔 Пока мы не нашли для вас идеального партнёра.\n\n"
            "🌱 Сообщество Baseline постоянно растёт.\n\n"
            "🎁 Пригласите друга в Baseline — возможно, именно он станет вашим следующим соперником на корте."
        ),
        "partner_card": "👤 *{name}*\nУровень: {level}\nРайон: {area}",
        "btn_invite": "📨 Пригласить",
        "btn_view_profile": "👀 Профиль",
        "invite_sent": "✉️ Приглашение отправлено {name}!",
        "btn_cancel": "❌ Отмена",
        "btn_done": "✅ Готово",
        "btn_back_menu": "🏠 Главное меню",
        "available_now_set": "🔥 Вы отмечены как доступный на следующие 2 часа!",
        "available_now_list_header": "🔥 *Игроки доступны сейчас:*",
        "available_now_empty": "😔 Сейчас нет доступных игроков.",
        "profile_header": "👤 *Ваш профиль*\n\n👤 Имя: {name}\n⭐ Уровень: {level}\n📖 Источник уровня: {level_source}\n📍 Район: {area}\n🎾 Корты: {courts}\n📊 Матчей: {matches}",
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
            "📊 NTRP {level}\n"
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
        "om_choose_level": "📊 *Уровень игры*\n\nВаш уровень: NTRP *{level}*",
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
            "📊 Уровень {level}\n"
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
            "📊 Уровень {level}\n"
            "{match_type}\n"
            "👥 1/{players} игроков"
        ),
        "om_btn_find_players": "🔍 Найти игроков",
        "om_btn_my_matches": "📋 Мои матчи",
        "om_my_matches_header": "📋 *Ваши матчи:*",
        # Find Players for Match
        "fpm_found": "👥 Мы нашли *{total}* игроков для вашего матча",
        "fpm_browse_card": "{name}\n📊 {level}\n📍 {area}",
        "fpm_not_found": (
            "😔 Сейчас мы не нашли подходящих игроков.\n\n"
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
            "📊 Уровень {level}\n"
            "👤 {organizer}"
        ),
        "inv_message_singles": (
            "🎾 *Вас приглашают на одиночный матч.*\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "📊 Уровень {level}\n"
            "👤 {organizer}"
        ),
        "inv_message_doubles": (
            "🎾 *Вас приглашают на парный матч.*\n"
            "Мы ещё ищем игроков.\n\n"
            "📅 {date}\n"
            "🕒 {time}\n"
            "📍 {court}\n"
            "📊 Уровень {level}\n"
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
        "inv_game_expired": "⚠️ Этот матч уже завершился и больше не принимает участников.",
        "inv_duplicate": "Уже приглашён.",
        "inv_delivery_failed": "⚠ К сожалению, нам не удалось отправить приглашение этому игроку.",
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
        # Leave match
        "leave_match_done": "✅ Вы покинули матч.",
        "leave_match_organizer": "⚠️ Хозяин не может покинуть матч. Используйте отмену матча.",
        "leave_match_not_participant": "⚠️ Вы не являетесь участником этого матча.",
        "leave_match_not_allowed": "⚠️ На этом этапе покинуть матч невозможно.",
        "leave_match_notification": "👤 {name} покинул(-а) ваш матч.",
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
