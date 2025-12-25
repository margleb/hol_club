from aiogram.fsm.state import State, StatesGroup


class EventsSG(StatesGroup):
    name = State()
    image = State()
    datetime = State()
    address_query = State()
    address_select = State()
    description = State()
    participation = State()
    price = State()
    age_group = State()
    notify = State()
    preview = State()
