from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Row, Select
from aiogram_dialog.widgets.text import Format

from app.bot.dialogs.account.getters import (
    get_account_age,
    get_account_gender,
    get_account_intro,
)
from app.bot.dialogs.account.handlers import (
    close_account_dialog,
    on_account_age_selected,
    on_account_gender_selected,
    start_account_intro,
)
from app.bot.states.account import AccountSG

account_dialog = Dialog(
    Window(
        Format("{intro_text}"),
        Button(
            text=Format("{intro_button}"),
            id="account_intro_start",
            on_click=start_account_intro,
        ),
        state=AccountSG.intro,
        getter=get_account_intro,
    ),
    Window(
        Format("{prompt}"),
        Select(
            Format("{item[0]}"),
            id="account_age_select",
            item_id_getter=lambda item: item[1],
            items="options",
            on_click=on_account_age_selected,
        ),
        Row(
            Button(
                text=Format("{back_button}"),
                id="account_age_back",
                on_click=close_account_dialog,
                when="can_back",
            ),
        ),
        state=AccountSG.age_group,
        getter=get_account_age,
    ),
    Window(
        Format("{prompt}"),
        Select(
            Format("{item[0]}"),
            id="account_gender_select",
            item_id_getter=lambda item: item[1],
            items="options",
            on_click=on_account_gender_selected,
        ),
        Row(
            Button(
                text=Format("{back_button}"),
                id="account_gender_back",
                on_click=close_account_dialog,
                when="can_back",
            ),
        ),
        state=AccountSG.gender,
        getter=get_account_gender,
    ),
)
