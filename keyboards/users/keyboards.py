from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


main_menu_builder = ReplyKeyboardBuilder()
main_menu_builder.add(
    KeyboardButton(text="🛍️ Каталог товаров"),
    KeyboardButton(text="🛒 Корзина"),
    KeyboardButton(text="👤 Профиль"),
    KeyboardButton(text="❓ Помощь"),
    KeyboardButton(text="🎁 Акции и скидки"),
)
main_menu_builder.adjust(2)
main_menu_keyboard = main_menu_builder.as_markup(resize_keyboard=True)


def create_categories_keyboard(categories):
    """
    Создает inline-клавиатуру с категориями товаров и кнопкой отмены.

    :param categories: Список категорий
    :return: InlineKeyboardMarkup
    """
    keyboard = []

    for category in categories:
        keyboard.append([InlineKeyboardButton(
            text=category,
            callback_data=f"category:{category}"
        )])

    keyboard.append([InlineKeyboardButton(
        text="🔙 Отмена",
        callback_data="cancel_catalog"
    )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_product_names_keyboard(product_names, category_name):
    """
    Создает inline-клавиатуру с подкатегориями товаров и кнопками навигации.

    :param product_names: Список подкатегорий
    :param category_name: название выбранной категории
    :return: InlineKeyboardMarkup
    """
    keyboard = []

    for product_name in product_names:
        keyboard.append([InlineKeyboardButton(
            text=product_name,
            callback_data=f"product_name:{category_name}:{product_name}"
        )])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад к категориям",
            callback_data="cancel_category_selection"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data="cancel_catalog"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
