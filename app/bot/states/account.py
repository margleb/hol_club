from aiogram.fsm.state import State, StatesGroup


class AccountSG(StatesGroup):
    gender = State()
    age_group = State()
