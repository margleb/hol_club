from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    event_details = State()
