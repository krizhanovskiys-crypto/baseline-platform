"""Handler utilities — common helpers used across multiple handlers."""
from aiogram.types import Message

from backend.app.bot.keyboards.keyboards import main_menu_keyboard
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import PlayerService


async def send_main_menu(message: Message, lang: str) -> None:
    """Send the main menu to a user."""
    await message.answer(
        t("main_menu", lang),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="Markdown",
    )


def get_player_lang(player: PlayerRead | None) -> str:
    """Return the player language or default."""
    return player.language or "en" if player else "en"
