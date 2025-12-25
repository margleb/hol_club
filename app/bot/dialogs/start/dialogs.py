from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Format

from app.bot.dialogs.start.getters import get_hello
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
        getter=get_hello,
        state=StartSG.start
    ),
)
