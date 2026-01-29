from aiogram.fsm.state import State, StatesGroup


class GeneralRegistrationSG(StatesGroup):
    gender = State()
    age_group = State()
