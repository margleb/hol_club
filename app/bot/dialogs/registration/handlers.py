from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.states.registration import GeneralRegistrationSG
from app.infrastructure.database.database.db import DB
from config.config import settings


def _get_chat_url(*, gender: str | None) -> str:
    if gender == "female":
        return getattr(settings.chat_links, "female_chat_url", None)
    return getattr(settings.chat_links, "male_chat_url", None)


def _get_channel_url() -> str | None:
    return getattr(settings.chat_links, "channel_url", None)


def _get_under_35_url() -> str:
    return getattr(settings.chat_links, "under_35_chat_url", None)


def _build_general_registration_keyboard(
    *,
    i18n: TranslatorRunner,
    channel_url: str,
    chat_url: str,
    under_35_url: str | None,
    gender: str | None,
) -> InlineKeyboardMarkup:
    chat_button_text = (
        i18n.general.registration.chat.female.button()
        if gender == "female"
        else i18n.general.registration.chat.male.button()
    )
    rows = [
        [
            InlineKeyboardButton(
                text=i18n.general.registration.channel.button(),
                url=channel_url,
            )
        ],
        [
            InlineKeyboardButton(
                text=chat_button_text,
                url=chat_url,
            )
        ],
    ]
    if under_35_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.under35.button(),
                    url=under_35_url,
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    channel_url = _get_channel_url()
    if i18n:
        if not channel_url or not chat_url:
            if callback.message:
                await callback.message.answer(
                    i18n.general.registration.links.missing()
                )
            await callback.answer()
            await dialog_manager.done()
            return
        lines = [
            i18n.general.registration.thanks(),
            i18n.general.registration.subscribe(
                channel=channel_url,
                chat_url=chat_url,
            ),
        ]
        under_35_url = _get_under_35_url() if _is_under_35(item_id) else None
        if under_35_url:
            lines.append(i18n.general.registration.under35())
        text = "\n\n".join(lines)
        keyboard = _build_general_registration_keyboard(
            i18n=i18n,
            channel_url=channel_url,
            chat_url=chat_url,
            under_35_url=under_35_url,
            gender=gender,
        )
    else:
        if not channel_url or not chat_url:
            text = "Missing channel or chat link configuration."
            keyboard = None
        else:
            under_35_url = _get_under_35_url() if _is_under_35(item_id) else None
            extra = (
                "\n\nUnder 35 chat is available."
                if under_35_url
                else ""
            )
            text = (
                "Thanks for registering!\n\n"
                f"Please subscribe to the channel {channel_url} and the chat."
                f"{extra}"
            )
            keyboard = None

    if callback.message:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()
    await dialog_manager.done()
