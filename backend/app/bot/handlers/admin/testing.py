"""Admin Center — Testing tools (Create Test Players, Reset Test Data,
Database Statistics). Unchanged from before Admin Center existed — only
now reachable behind the PIN/session gate in auth.py instead of the old
flat DEVELOPER_IDS check.

As of Sprint 11 Phase 2.2, this module's own submenu is no longer the
Admin Center root — dashboard.py owns that screen now and calls
`show_testing_menu()` when the operator taps "Testing" there.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import authorized_role, lang_for
from backend.app.bot.handlers.helpers import send_main_menu
from backend.app.bot.keyboards.keyboards import dev_menu_keyboard
from backend.app.bot.texts import t
from backend.app.services.dev_service import DevService

router = Router(name="admin_testing")


async def show_testing_menu(message: Message, lang: str) -> None:
    """Testing's own submenu — reached via the Dashboard's Testing button."""
    await message.answer(
        t("dev_menu_header", lang),
        reply_markup=dev_menu_keyboard(lang),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "dev:create_players")
async def dev_create_players(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    dev_svc = DevService(session)
    count = await dev_svc.create_test_players()
    key = "dev_players_created" if count > 0 else "dev_players_already_exist"
    await callback.message.answer(t(key, lang, count=count), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dev:reset_data")
async def dev_reset_data(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    dev_svc = DevService(session)
    count = await dev_svc.reset_test_data()
    key = "dev_data_reset" if count > 0 else "dev_nothing_to_reset"
    await callback.message.answer(t(key, lang, count=count), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dev:stats")
async def dev_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    dev_svc = DevService(session)
    stats = await dev_svc.get_stats()
    await callback.message.answer(t("dev_stats", lang, **stats), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dev:exit")
async def dev_exit(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()
