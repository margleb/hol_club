from aiogram.fsm.state import State, StatesGroup


class StartSG(StatesGroup):
    start = State()
    user_events_list = State()
    user_event_details = State()
    user_event_attend_code = State()
    admin_partner_commissions_list = State()
    admin_partner_commission_edit = State()
    admin_partner_requests_list = State()
    admin_partner_request_details = State()
    admin_registration_partners_list = State()
    admin_registration_pending_list = State()
    admin_registration_message_user = State()
    partner_events_list = State()
    partner_event_details = State()
    partner_event_pending_list = State()
    partner_event_pending_details = State()
    partner_event_confirmed_list = State()
