from aiogram.fsm.state import State, StatesGroup


class CartState(StatesGroup):
    viewing_cart = State()
    last_product_id = State()
