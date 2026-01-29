from aiogram.fsm.state import State, StatesGroup


class AccountSG(StatesGroup):
    intro = State()
    age_group = State()
    gender = State()
    intent = State()
    final = State()
