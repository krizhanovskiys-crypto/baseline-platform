"""Find Partner handler."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.bot.keyboards.keyboards import partner_actions_keyboard
from backend.app.bot.texts import t
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="find_partner")

_TRIGGER_TEXTS = {"🎾 Find Partner", "🎾 Знайти партнера", "🎾 Найти партнёра"}


@router.message(F.text.in_(_TRIGGER_TEXTS))
async def find_partner(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    await message.answer(
        t("finding_partners", lang, area=player.home_area, level=player.skill_level),
        parse_mode="Markdown",
    )

    partners = await service.find_partners(
        telegram_id=user.id,
        area=player.home_area or "",
        skill_level=player.skill_level or 3.0,
    )

    if not partners:
        await message.answer(t("no_partners", lang), parse_mode="Markdown")
        return

    for partner in partners:
        await message.answer(
            t(
                "partner_card",
                lang,
                name=partner.first_name,
                level=partner.skill_level,
                area=partner.home_area or "—",
                rating=partner.rating,
            ),
            reply_markup=partner_actions_keyboard(lang, partner.telegram_id),
            parse_mode="Markdown",
        )


@router.callback_query(F.data.startswith("invite:"))
async def invite_player(callback: CallbackQuery, session: AsyncSession) -> None:
    invitee_tid = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    user = callback.from_user
    service = PlayerService(session)
    current = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(current)

    invitee = await service.get_by_telegram_id(invitee_tid)
    name = invitee.first_name if invitee else "Player"

    await callback.answer(t("invite_sent", lang, name=name), show_alert=True)


@router.callback_query(F.data.startswith("view_profile:"))
async def view_partner_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    target_tid = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    user = callback.from_user
    service = PlayerService(session)
    current = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(current)
    target = await service.get_by_telegram_id(target_tid)

    if not target:
        await callback.answer(t("error_generic", lang), show_alert=True)
        return

    courts = ", ".join(target.preferred_courts or []) or "—"
    text = t(
        "profile_header",
        lang,
        name=target.first_name,
        level=target.skill_level,
        area=target.home_area or "—",
        courts=courts,
        rating=target.rating,
        matches=target.matches_played,
    )
    await callback.message.answer(text, parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()
