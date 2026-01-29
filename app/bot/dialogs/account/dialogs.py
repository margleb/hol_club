from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Row, Select, Url
from aiogram_dialog.widgets.text import Format

from app.bot.dialogs.account.getters import (
    get_account_age,
    get_account_final,
    get_account_gender,
    get_account_intent,
    get_account_intro,
)
from app.bot.dialogs.account.handlers import (
    close_account_dialog,
    finish_account_final,
    on_account_age_selected,
    on_account_gender_selected,
    on_account_intent_selected,
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
    Window(
        Format("{prompt}"),
        Select(
            Format("{item[0]}"),
            id="account_intent_select",
            item_id_getter=lambda item: item[1],
            items="options",
            on_click=on_account_intent_selected,
        ),
        Format("{note}"),
        Row(
            Button(
                text=Format("{back_button}"),
                id="account_intent_back",
                on_click=close_account_dialog,
                when="can_back",
            ),
        ),
        state=AccountSG.intent,
        getter=get_account_intent,
    ),
    Window(
        Format("{final_text}"),
        Row(
            Url(
                text=Format("{channel_button}"),
                url=Format("{channel_url}"),
                id="account_final_channel",
                when="has_channel_url",
            ),
            Url(
                text=Format("{chat_button}"),
                url=Format("{chat_url}"),
                id="account_final_chat",
                when="has_chat_url",
            ),
        ),
        Button(
            text=Format("{final_button}"),
            id="account_final_ok",
            on_click=finish_account_final,
        ),
        state=AccountSG.final,
        getter=get_account_final,
    ),
)
