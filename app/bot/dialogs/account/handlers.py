from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button
from fluentogram import TranslatorRunner

from app.bot.states.account import AccountSG
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB


async def start_account_intro(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.age_group)


async def close_account_dialog(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.done()


async def on_account_gender_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    age_group = dialog_manager.dialog_data.get("age_group")
    db: DB | None = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner | None = dialog_manager.middleware_data.get("i18n")
    user = callback.from_user
    if db and user:
        await db.users.update_profile(
            user_id=user.id,
            gender=item_id,
            age_group=age_group,
        )
    if i18n and callback.message:
        await callback.message.answer(i18n.account.updated())
    await callback.answer()
    start_data = dialog_manager.start_data or {}
    if start_data.get("force_profile", False):
        await dialog_manager.start(
            state=StartSG.start,
            mode=StartMode.RESET_STACK,
        )
        return
    await dialog_manager.done()


async def on_account_age_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["age_group"] = item_id
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.gender)
