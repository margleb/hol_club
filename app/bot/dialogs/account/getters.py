from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.dialogs.general_registration.getters import AGE_GROUPS


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
