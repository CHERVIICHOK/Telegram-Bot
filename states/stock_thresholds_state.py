from aiogram.fsm.state import State, StatesGroup


class StockThresholdState(StatesGroup):
    select_category = State()
    select_product = State()
    enter_threshold = State()
    confirm_threshold = State()
