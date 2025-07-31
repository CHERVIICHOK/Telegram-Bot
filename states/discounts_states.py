from aiogram.fsm.state import State, StatesGroup

class DiscountStates(StatesGroup):
    waiting_for_promo_code = State()