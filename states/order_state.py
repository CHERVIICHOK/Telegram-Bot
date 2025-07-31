# states/order_state.py
from aiogram.fsm.state import StatesGroup, State


class OrderState(StatesGroup):
    name = State()
    phone = State()
    delivery_date = State()
    delivery_time = State()
    delivery_type = State()
    delivery_address = State()
    payment_method = State()
    comment = State()
    promo_code = State()  # Новое состояние для промокода
    confirmation = State()
    edit_selection = State()