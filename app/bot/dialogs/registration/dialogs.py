from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Select
from aiogram_dialog.widgets.text import Format

from app.bot.dialogs.registration.getters import (
    get_general_registration_age,
    get_general_registration_gender,
)
from app.bot.dialogs.registration.handlers import (
    on_general_age_selected,
    on_general_gender_selected,
)
from app.bot.states.registration import GeneralRegistrationSG

general_registration_dialog = Dialog(
    Window(
        Format("{prompt}"),
        Select(
            Format("{item[0]}"),
            id="general_gender_select",
            item_id_getter=lambda item: item[1],
            items="options",
            on_click=on_general_gender_selected,
        ),
        getter=get_general_registration_gender,
        state=GeneralRegistrationSG.gender,
    ),
    Window(
        Format("{prompt}"),
        Select(
            Format("{item[0]}"),
            id="general_age_select",
            item_id_getter=lambda item: item[1],
            items="options",
            on_click=on_general_age_selected,
        ),
        getter=get_general_registration_age,
        state=GeneralRegistrationSG.age_group,
    ),
)
