from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    user_events_list = State()
    user_event_details = State()
    user_event_dialog = State()
    admin_registration_pending_details = State()
    admin_events_list = State()
    admin_event_details = State()
    admin_event_registrations_list = State()
    admin_event_confirmed_registrations_list = State()
    admin_registration_confirmed_details = State()
    admin_event_dialog = State()
