from aiogram.fsm.state import State, StatesGroup


class AdminContactSG(StatesGroup):
    waiting_payment_proof = State()
