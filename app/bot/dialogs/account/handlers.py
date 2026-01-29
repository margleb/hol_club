from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from fluentogram import TranslatorRunner

from app.bot.states.account import AccountSG
from app.infrastructure.database.database.db import DB


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
    await dialog_manager.switch_to(AccountSG.intro)


async def back_from_gender(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.age_group)


async def back_from_intent(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.gender)


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
    await callback.answer()
    dialog_manager.dialog_data["gender"] = item_id
    if dialog_manager.dialog_data.get("edit_target") == "gender":
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.intent)


async def on_account_age_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["age_group"] = item_id
    await callback.answer()
    if dialog_manager.dialog_data.get("edit_target") == "age_group":
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.gender)


async def on_account_intent_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    gender = dialog_manager.dialog_data.get("gender")
    age_group = dialog_manager.dialog_data.get("age_group")
    dialog_manager.dialog_data["intent"] = item_id
    db: DB | None = dialog_manager.middleware_data.get("db")
    user = callback.from_user
    if db and user:
        await db.users.update_profile(
            user_id=user.id,
            gender=gender,
            age_group=age_group,
            intent=item_id,
        )
    await callback.answer()
    if dialog_manager.dialog_data.get("edit_target") == "intent":
        dialog_manager.dialog_data.pop("edit_target", None)
        await dialog_manager.switch_to(AccountSG.summary)
        return
    await dialog_manager.switch_to(AccountSG.summary)


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


async def edit_account_intent(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_target"] = "intent"
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.intent)


async def continue_from_summary(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(AccountSG.final)
