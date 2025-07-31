from aiogram.fsm.state import State, StatesGroup


class AdminPromoStates(StatesGroup):
    enter_code = State()
    enter_description = State()
    choose_discount_type = State()
    enter_discount_value = State()
    enter_min_order_amount = State()
    enter_end_date = State()
    enter_max_uses = State()
    confirm_creation = State()


class AdminDailyDealStates(StatesGroup):
    enter_product_id = State()
    enter_description = State()
    choose_discount_type = State()
    enter_discount_value = State()
    enter_deal_date = State()
    confirm_creation = State()


class AdminActionStates(StatesGroup):
    enter_title = State()
    enter_description = State()
    choose_target_type = State()
    choose_category = State()
    choose_product_name = State()
    choose_flavor = State()
    choose_discount_type = State()
    enter_discount_value = State()
    enter_start_date = State()
    enter_end_date = State()
    confirm_creation = State()
