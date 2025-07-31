# states/product_image_state.py
from aiogram.fsm.state import State, StatesGroup


class ProductImageState(StatesGroup):
    select_category = State()
    select_product = State()
    upload_image = State()
    confirm = State()
