from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.dialogs.general_registration.getters import AGE_GROUPS
from config.config import settings


async def get_account_intro(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    return {
        "intro_text": i18n.account.intro.text(),
        "intro_button": i18n.account.intro.button(),
    }


async def get_account_gender(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    start_data = dialog_manager.start_data or {}
    return {
        "prompt": i18n.account.gender.prompt(),
        "options": [
            (i18n.general.registration.gender.male(), "male"),
            (i18n.general.registration.gender.female(), "female"),
        ],
        "back_button": i18n.back.button(),
        "can_back": not start_data.get("force_profile", False),
    }


async def get_account_age(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    start_data = dialog_manager.start_data or {}
    return {
        "prompt": i18n.account.age.prompt(),
        "options": [
            (i18n.general.registration.age.group(range=age_group), age_group)
            for age_group in AGE_GROUPS
        ],
        "back_button": i18n.back.button(),
        "can_back": not start_data.get("force_profile", False),
    }


async def get_account_intent(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    return {
        "prompt": i18n.account.intent.prompt(),
        "options": [
            (i18n.account.intent.hot(), "hot"),
            (i18n.account.intent.warm(), "warm"),
            (i18n.account.intent.cold(), "cold"),
        ],
        "note": i18n.account.intent.note(),
        "back_button": i18n.back.button(),
    }


async def get_account_final(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    gender = dialog_manager.dialog_data.get("gender")
    channel_url = getattr(settings.chat_links, "channel_url", None)
    if not channel_url:
        events_channel = settings.get("events_channel")
        if isinstance(events_channel, str) and events_channel.strip():
            slug = events_channel.strip().lstrip("@")
            channel_url = f"https://t.me/{slug}"

    if gender == "female":
        chat_url = getattr(settings.chat_links, "female_chat_url", None)
        chat_button = i18n.account.final.chat.female.button()
    else:
        chat_url = getattr(settings.chat_links, "male_chat_url", None)
        chat_button = i18n.account.final.chat.male.button()

    return {
        "final_text": i18n.account.final.text(),
        "final_button": i18n.account.final.button(),
        "channel_button": i18n.account.final.channel.button(),
        "channel_url": channel_url or "",
        "has_channel_url": bool(channel_url),
        "chat_button": chat_button,
        "chat_url": chat_url or "",
        "has_chat_url": bool(chat_url),
    }
