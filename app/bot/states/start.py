from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    partner_events_list = State()
    partner_event_details = State()
    partner_event_pending_list = State()
    partner_event_pending_details = State()
    partner_event_confirmed_list = State()
