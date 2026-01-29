from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Group, Row, Select, Url
from aiogram_dialog.widgets.text import Format

from app.bot.dialogs.account.getters import (
    get_account_age,
    get_account_final,
    get_account_gender,
    get_account_intent,
    get_account_intro,
    get_account_summary,
)
from app.bot.dialogs.account.handlers import (
    back_from_age,
    back_from_gender,
    back_from_intent,
    close_account_dialog,
    continue_from_summary,
    edit_account_age,
    edit_account_gender,
    edit_account_intent,
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
        Group(
            Select(
                Format("{item[0]}"),
                id="account_age_select",
                item_id_getter=lambda item: item[1],
                items="options",
                on_click=on_account_age_selected,
            ),
            width=1,
        ),
        Row(
            Button(
                text=Format("{back_button}"),
                id="account_age_back",
                on_click=back_from_age,
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
                on_click=back_from_gender,
            ),
        ),
        state=AccountSG.gender,
        getter=get_account_gender,
    ),
    Window(
        Format("{prompt}"),
        Group(
            Select(
                Format("{item[0]}"),
                id="account_intent_select",
                item_id_getter=lambda item: item[1],
                items="options",
                on_click=on_account_intent_selected,
            ),
            width=1,
        ),
        Row(
            Button(
                text=Format("{back_button}"),
                id="account_intent_back",
                on_click=back_from_intent,
            ),
        ),
        state=AccountSG.intent,
        getter=get_account_intent,
    ),
    Window(
        Format("{summary_title}"),
        Format("{summary_age_label}: {summary_age_value}"),
        Format("{summary_gender_label}: {summary_gender_value}"),
        Format("{summary_intent_label}: {summary_intent_value}"),
        Group(
            Button(
                text=Format("{edit_age_button}"),
                id="account_summary_edit_age",
                on_click=edit_account_age,
            ),
            Button(
                text=Format("{edit_gender_button}"),
                id="account_summary_edit_gender",
                on_click=edit_account_gender,
            ),
            Button(
                text=Format("{edit_intent_button}"),
                id="account_summary_edit_intent",
                on_click=edit_account_intent,
            ),
            width=1,
        ),
        Button(
            text=Format("{continue_button}"),
            id="account_summary_continue",
            on_click=continue_from_summary,
        ),
        state=AccountSG.summary,
        getter=get_account_summary,
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
        state=AccountSG.final,
        getter=get_account_final,
    ),
)
