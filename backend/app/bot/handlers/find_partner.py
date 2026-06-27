"""Find Partner handler — one-at-a-time browsing with FSM pagination."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import partner_card_keyboard
from backend.app.bot.states.states import FindPartnerStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="find_partner")

_TRIGGER_TEXTS = {"🎾 Find Partner", "🎾 Знайти партнера", "🎾 Найти партнёра"}


def _build_card(partner: PlayerRead, lang: str, total: int) -> tuple[str, object]:
    """Return (text, keyboard) for a partner card."""
    level_source_key = f"level_source_card_{partner.level_source or 'self_rated'}"
    level_source_line = t(level_source_key, lang)
    courts = ", ".join(partner.preferred_courts or []) or "—"
    text = t(
        "partner_card_v2",
        lang,
        name=partner.first_name,
        level=partner.skill_level,
        level_source_line=level_source_line,
        area=partner.home_area or "—",
        courts=courts,
    )
    keyboard = partner_card_keyboard(lang, partner.username, show_next=total > 1)
    return text, keyboard


@router.message(F.text.in_(_TRIGGER_TEXTS))
async def find_partner(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    partners = await service.find_partners(
        telegram_id=user.id,
        area=player.home_area or "",
        skill_level=player.skill_level or 3.0,
        my_courts=player.preferred_courts or [],
    )

    if not partners:
        await message.answer(t("no_partners_friendly", lang), parse_mode="Markdown")
        return

    partner_ids = [p.telegram_id for p in partners]
    await state.set_state(FindPartnerStates.browsing)
    await state.update_data(partner_ids=partner_ids, index=0, lang=lang)

    text, keyboard = _build_card(partners[0], lang, total=len(partners))
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(FindPartnerStates.browsing, F.data == "fp:next")
async def fp_next(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    partner_ids: list[int] = data["partner_ids"]
    index: int = (data["index"] + 1) % len(partner_ids)
    lang: str = data.get("lang", "en")
    await state.update_data(index=index)

    service = PlayerService(session)
    partner = await service.get_by_telegram_id(partner_ids[index])
    if not partner:
        await callback.answer()
        return

    text, keyboard = _build_card(partner, lang, total=len(partner_ids))
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "fp:menu")
async def fp_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "fp:no_contact")
async def fp_no_contact(callback: CallbackQuery, session: AsyncSession) -> None:
    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer(t("no_contact_available", lang), show_alert=True)
