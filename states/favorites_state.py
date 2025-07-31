from aiogram.fsm.state import State, StatesGroup


class FavoritesState(StatesGroup):
    viewing_favorites = State()
    viewing_item = State()
    browsing_categories = State()
    browsing_products = State()
    browsing_flavors = State()
