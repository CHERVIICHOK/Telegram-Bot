from aiogram.fsm.state import State, StatesGroup


class StaffAddStates(StatesGroup):
    telegram_id = State()
    first_name = State()
    last_name = State()
    phone = State()
    role = State()
    access_level = State()
    confirm = State()


class StaffEditStates(StatesGroup):
    new_role = State()
    new_access_level = State()
    confirm_delete = State()


class StaffStatusCreateState(StatesGroup):
    status_name = State()
    status_description = State()
    confirm = State()
