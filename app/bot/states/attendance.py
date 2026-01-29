from aiogram.fsm.state import State, StatesGroup


class AttendanceSG(StatesGroup):
    waiting_code = State()
