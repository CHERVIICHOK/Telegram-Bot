from aiogram.fsm.state import State, StatesGroup


class CatalogState(StatesGroup):
    browsing_categories = State()  # Просмотр категорий
    browsing_products = State()  # Просмотр списка товаров в категории
    viewing_product = State()  # Просмотр детальной информации о товаре
    adding_to_cart = State()  # Добавление товара в корзину
