from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.dialogs.registration.getters import AGE_GROUPS
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
        chat_label = i18n.account.final.chat.female()
    else:
        chat_url = getattr(settings.chat_links, "male_chat_url", None)
        chat_button = i18n.account.final.chat.male.button()
        chat_label = i18n.account.final.chat.male()

    channel_label = i18n.account.final.channel()

    text = i18n.account.final.text(
        channel=channel_label,
        chat=chat_label,
    )

    return {
        "final_text": text,
        "channel_button": i18n.account.final.channel.button(),
        "channel_url": channel_url or "",
        "has_channel_url": bool(channel_url),
        "chat_button": chat_button,
        "chat_url": chat_url or "",
        "has_chat_url": bool(chat_url),
    }


async def get_account_summary(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    start_data = dialog_manager.start_data or {}
    db = dialog_manager.middleware_data.get("db")
    user = dialog_manager.middleware_data.get("event_from_user")

    if db and user:
        record = await db.users.get_user_record(user_id=user.id)
    else:
        record = None

    gender = dialog_manager.dialog_data.get("gender") or (record.gender if record else None)
    age_group = dialog_manager.dialog_data.get("age_group") or (record.age_group if record else None)
    temperature = (
        dialog_manager.dialog_data.get("temperature")
        or (record.temperature if record else None)
        or "cold"
    )

    dialog_manager.dialog_data["gender"] = gender
    dialog_manager.dialog_data["age_group"] = age_group
    dialog_manager.dialog_data["temperature"] = temperature

    if gender == "female":
        gender_label = i18n.general.registration.gender.female()
    elif gender == "male":
        gender_label = i18n.general.registration.gender.male()
    else:
        gender_label = "-"

    return {
        "summary_title": i18n.account.summary.title(),
        "summary_age_label": i18n.account.summary.age(),
        "summary_gender_label": i18n.account.summary.gender(),
        "summary_age_value": age_group or "-",
        "summary_gender_value": gender_label,
        "edit_age_button": i18n.account.summary.edit.age.button(),
        "edit_gender_button": i18n.account.summary.edit.gender.button(),
        "continue_button": i18n.account.summary.confirm.button(),
        "close_button": i18n.account.summary.close.button(),
        "show_continue": not start_data.get("edit_profile", False),
        "show_close": bool(start_data.get("edit_profile", False)),
    }
