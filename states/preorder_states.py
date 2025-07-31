from aiogram.fsm.state import State, StatesGroup


class AddPreorderProduct(StatesGroup):
    """Состояния для добавления товара в предзаказы"""
    category = State()
    product_name = State()
    flavor = State()
    description = State()
    price = State()
    expected_date = State()
    image = State()
    confirm = State()
    edit_field = State()


class BulkUploadProducts(StatesGroup):
    """Состояния для массовой загрузки товаров"""
    upload_file = State()
    confirm = State()
