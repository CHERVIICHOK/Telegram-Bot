from aiogram.fsm.state import StatesGroup, State


class HelpState(StatesGroup):
    main_help = State()
    faq = State()
    contact_support = State()
    delivery_info = State()
    payment_info = State()
    refund_policy = State()
    feedback_comment = State()
    feedback_rating = State()