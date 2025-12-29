from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    events_list = State()
    event_details = State()
    partner_events_list = State()
    partner_event_details = State()
    partner_event_registrations = State()
    partner_event_pending_payments = State()
