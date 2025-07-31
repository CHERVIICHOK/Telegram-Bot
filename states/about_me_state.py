from aiogram.fsm.state import State, StatesGroup


class AboutMeStates(StatesGroup):
    MAIN_MENU = State()

    # Личные данные
    PERSONAL_INFO_MENU = State()
    EDITING_FIRST_NAME = State()
    EDITING_LAST_NAME = State()
    EDITING_BIRTH_DATE = State()
    SELECTING_GENDER = State()
    EDITING_EMAIL = State()
    EDITING_PHONE = State()

    # Адреса
    ADDRESS_MENU = State()
    ADDING_ADDRESS = State()
    EDITING_ADDRESS = State()
    EDITING_COURIER_INSTRUCTIONS = State()  # Новое состояние

    # Время доставки
    DELIVERY_TIME_MENU = State()
    SELECTING_START_TIME = State()
    SELECTING_END_TIME = State()
