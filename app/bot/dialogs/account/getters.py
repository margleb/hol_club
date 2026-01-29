from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.dialogs.general_registration.getters import AGE_GROUPS


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
