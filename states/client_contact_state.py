from aiogram.fsm.state import State, StatesGroup


class ClientContactStates(StatesGroup):
    """Состояния для функции связи с клиентом"""
    waiting_for_client_id = State()
    waiting_for_message_type = State()
    waiting_for_text_message = State()
    waiting_for_image = State()
    waiting_for_image_caption = State()
    confirm_sending = State()
