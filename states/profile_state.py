from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    MAIN = State()
    TRACKING_ORDERS = State()
    ORDER_DETAIL = State()
    ORDER_HISTORY = State()

    WAITING_FOR_DELIVERY_RATING = State()
    WAITING_FOR_DELIVERY_COMMENT = State()
    WAITING_FOR_PRODUCT_LIST = State()
    WAITING_FOR_PRODUCT_RATING = State()
    WAITING_FOR_PRODUCT_COMMENT = State()