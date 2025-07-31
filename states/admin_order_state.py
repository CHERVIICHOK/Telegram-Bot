from aiogram.fsm.state import State, StatesGroup


class AdminOrderProcess(StatesGroup):
    """Состояния для обработки заказа администратором"""
    WAITING_ORDER_INFO = State()  # Ожидание ввода информации о заказе
    WAITING_DISCOUNT = State()  # Ожидание ввода скидки
    CONFIRM_ORDER = State()  # Подтверждение заказа
