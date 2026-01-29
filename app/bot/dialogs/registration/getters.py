from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

AGE_GROUPS = ("25-35", "35-45", "45-55", "55-65")


async def get_general_registration_gender(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    return {
        "prompt": i18n.general.registration.gender.prompt(),
        "options": [
            (i18n.general.registration.gender.male(), "male"),
            (i18n.general.registration.gender.female(), "female"),
        ],
    }


async def get_general_registration_age(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, object]:
    return {
        "prompt": i18n.general.registration.age.prompt(),
        "options": [
            (i18n.general.registration.age.group(range=age_group), age_group)
            for age_group in AGE_GROUPS
        ],
    }
