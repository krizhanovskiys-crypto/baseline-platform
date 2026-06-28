"""Available Now handler."""
import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.bot.texts import t
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="available_now")

_TRIGGER_TEXTS = {"🔥 Available Now", "🔥 Доступний зараз", "🔥 Доступен сейчас"}


@router.message(F.text.in_(_TRIGGER_TEXTS))
async def available_now_menu(message: Message, session: AsyncSession) -> None:
    """Show available players and let user mark themselves as available."""
    user = message.from_user
    if not user:
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    # Mark self as available
    await service.set_available_now(user.id)
    await message.answer(t("available_now_set", lang), parse_mode="Markdown")

    # Show others
    available = await service.get_available_now()
    # Exclude self from display
    others = [p for p in available if p.telegram_id != user.id]

    if not others:
        await message.answer(t("available_now_empty", lang), parse_mode="Markdown")
        return

    await message.answer(t("available_now_list_header", lang), parse_mode="Markdown")
    for p in others:
        await message.answer(
            t(
                "partner_card",
                lang,
                name=p.first_name,
                level=p.skill_level,
                area=p.home_area or "—",
            ),
            parse_mode="Markdown",
        )
