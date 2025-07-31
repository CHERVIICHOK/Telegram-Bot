from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_empty_favorites_keyboard():
    """Клавиатура для пустого списка избранного"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="↩️ Вернуться в главное меню",
        callback_data="favorites:back_to_main"
    ))

    builder.row(InlineKeyboardButton(
        text="🛍️ Каталог товаров",
        callback_data=f"start_catalog_browsing"
    ))

    return builder.as_markup()


def get_favorites_keyboard(favorites: List[tuple], current_index: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура для навигации по избранному"""
    builder = InlineKeyboardBuilder()

    if not favorites:
        builder.row(InlineKeyboardButton(
            text="💔 Список избранного пуст",
            callback_data="favorites:empty"
        ))
        builder.row(InlineKeyboardButton(
            text="↩️ В главное меню",
            callback_data="favorites:back_to_main"
        ))
        return builder.as_markup()

    current_product = favorites[current_index]
    product_id = current_product[0]
    total_items = len(favorites)
    total_pages = total_items

    navigation_buttons: List[InlineKeyboardButton] = []

    if current_index > 0:
        navigation_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"favorites:prev:{current_index}"
        ))
    else:
        navigation_buttons.append(InlineKeyboardButton(
            text="➖",
            callback_data="favorites:noop"
        ))

    navigation_buttons.append(InlineKeyboardButton(
        text=f"{current_index + 1}/{total_pages}",
        callback_data="favorites:noop"
    ))

    if current_index < total_items - 1:
        navigation_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"favorites:next:{current_index}"
        ))
    else:
        navigation_buttons.append(InlineKeyboardButton(
            text="➖",
            callback_data="favorites:noop"
        ))

    builder.row(*navigation_buttons)

    builder.row(InlineKeyboardButton(
        text="🛒 Добавить в корзину",
        callback_data=f"favorites:add_to_cart:{product_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="💔 Удалить из избранного",
        callback_data=f"favorites:remove:{product_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="↩️ В главное меню",
        callback_data="favorites:back_to_main"
    ))

    return builder.as_markup()
