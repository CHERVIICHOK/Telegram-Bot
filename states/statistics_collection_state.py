from aiogram.fsm.state import StatesGroup, State

class StatisticsState(StatesGroup):
    """Состояния для работы со статистикой"""
    warehouse_value = State()  # Состояние для расчета стоимости склада
    sales_statistics = State()  # Состояние для просмотра статистики продаж
    profit_statistics = State()  # Состояние для просмотра статистики прибыли