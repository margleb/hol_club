from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.states.general_registration import GeneralRegistrationSG
from app.infrastructure.database.database.db import DB
from config.config import settings

DEFAULT_FEMALE_CHAT_URL = "https://t.me/+rf9C4DvuKzY4YTY6"
DEFAULT_MALE_CHAT_URL = "https://t.me/+F5GqT7jJGA1mNmFi"
DEFAULT_UNDER_35_CHAT_URL = "https://t.me/+xGSjpFlnbHgyZjE6"


def _get_chat_url(*, gender: str | None) -> str:
    if gender == "female":
        return (
            getattr(settings.general_registration, "female_chat_url", None)
            or DEFAULT_FEMALE_CHAT_URL
        )
    return (
        getattr(settings.general_registration, "male_chat_url", None)
        or DEFAULT_MALE_CHAT_URL
    )


def _get_under_35_url() -> str:
    return (
        getattr(settings.general_registration, "under_35_chat_url", None)
        or DEFAULT_UNDER_35_CHAT_URL
    )


def _is_under_35(age_group: str) -> bool:
    parts = age_group.split("-", 1)
    if len(parts) != 2:
        return False
    try:
        upper = int(parts[1])
    except ValueError:
        return False
    return upper <= 35


async def on_general_gender_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["gender"] = item_id
    await callback.answer()
    await dialog_manager.switch_to(GeneralRegistrationSG.age_group)


async def on_general_age_selected(
    callback: CallbackQuery,
    widget: object,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["age_group"] = item_id
    gender = dialog_manager.dialog_data.get("gender")

    db: DB | None = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner | None = dialog_manager.middleware_data.get("i18n")
    user = callback.from_user
    if db and user:
        await db.users.update_profile(
            user_id=user.id,
            gender=gender,
            age_group=item_id,
        )

    chat_url = _get_chat_url(gender=gender)
    if i18n:
        lines = [
            i18n.general.registration.thanks(),
            i18n.general.registration.subscribe(
                channel="@hol_club",
                chat_url=chat_url,
            ),
        ]
        if _is_under_35(item_id):
            lines.append(
                i18n.general.registration.under35(url=_get_under_35_url())
            )
        text = "\n\n".join(lines)
    else:
        extra = ""
        if _is_under_35(item_id):
            extra = f"\n\n{_get_under_35_url()}"
        text = (
            "Спасибо за регистрацию!\n\n"
            f"Подпишитесь на канал @hol_club и чат: {chat_url}{extra}"
        )

    if callback.message:
        await callback.message.answer(text)
    await callback.answer()
    await dialog_manager.done()
