from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    events_list = State()
    event_details = State()
