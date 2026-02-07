from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    user_events_list = State()
    user_event_details = State()
    user_event_attend_code = State()
    partner_events_list = State()
    partner_event_details = State()
    partner_event_pending_list = State()
    partner_event_pending_details = State()
    partner_event_confirmed_list = State()
