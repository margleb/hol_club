from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.kbd import Button, Start
from aiogram_dialog.widgets.text import Format

from app.bot.dialogs.start.getters import get_hello
from app.bot.dialogs.start.handlers import show_partner_requests_list
from app.bot.states.start import StartSG
from app.bot.states.events import EventsSG

start_dialog = Dialog(
    Window(
        Format('{hello}'),
        Start(
            text=Format("{create_event_button}"),
            id="start_event_creation",
            state=EventsSG.name,
            mode=StartMode.NORMAL,
            when="can_create_event",
        ),
        Button(
            text=Format("{partner_requests_button}"),
            id="partner_requests_list",
            on_click=show_partner_requests_list,
            when="can_manage_partner_requests",
        ),
        getter=get_hello,
        state=StartSG.start
    ),
)
