from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from app.bot.states.account import AccountSG
from app.infrastructure.database.database.db import DB


async def _save_profile(
    dialog_manager: DialogManager,
    user_id: int,
) -> None:
    db: DB | None = dialog_manager.middleware_data.get("db")
    if not db:
        return

    gender = dialog_manager.dialog_data.get("gender")
    age_group = dialog_manager.dialog_data.get("age_group")
    temperature = dialog_manager.dialog_data.get("temperature") or "cold"
    dialog_manager.dialog_data["temperature"] = temperature
    if not gender or not age_group:
        return

    await db.users.update_profile(
        user_id=user_id,
        gender=gender,
        age_group=age_group,
        temperature=temperature,
    )


async def start_account_intro(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.age_group)


async def back_from_age(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    if dialog_manager.dialog_data.get("edit_target"):
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.intro)


async def back_from_gender(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    if dialog_manager.dialog_data.get("edit_target"):
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.age_group)


async def close_account_dialog(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if callback.from_user:
        await _save_profile(dialog_manager, callback.from_user.id)
    await callback.answer()
    await dialog_manager.done()


async def on_account_gender_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["gender"] = item_id
    if callback.from_user:
        await _save_profile(dialog_manager, callback.from_user.id)
    await callback.answer()
    if dialog_manager.dialog_data.get("edit_target") == "gender":
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.summary)


async def on_account_age_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["age_group"] = item_id
    if callback.from_user:
        await _save_profile(dialog_manager, callback.from_user.id)
    await callback.answer()
    if dialog_manager.dialog_data.get("edit_target") == "age_group":
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.gender)


async def edit_account_age(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_target"] = "age_group"
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.age_group)


async def edit_account_gender(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_target"] = "gender"
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.gender)


async def continue_from_summary(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if callback.from_user:
        await _save_profile(dialog_manager, callback.from_user.id)
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.final)
