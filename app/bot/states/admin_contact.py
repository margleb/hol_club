from aiogram.fsm.state import State, StatesGroup


class AdminContactSG(StatesGroup):
    waiting_reply_text = State()
    waiting_admin_text = State()
    waiting_payment_proof = State()
