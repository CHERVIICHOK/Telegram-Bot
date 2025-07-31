from aiogram.fsm.state import State, StatesGroup


class TimeoutSettingsStates(StatesGroup):
    entering_custom_time = State()
    entering_custom_interval = State()
    entering_notification_text = State()