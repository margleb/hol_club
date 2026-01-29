from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    partner_events_list = State()
    partner_event_details = State()
