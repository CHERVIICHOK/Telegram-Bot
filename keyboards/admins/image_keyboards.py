# keyboards/admins/image_keyboards.py
import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_paginated_keyboard(items, current_page=1, items_per_page=10, callback_prefix="item",
                              back_callback="back", show_back=True):
    """
    Создает пагинированную inline-клавиатуру

    :param items: список элементов для отображения
    :param current_page: текущая страница
    :param items_per_page: количество элементов на странице
    :param callback_prefix: префикс для callback_data
    :param back_callback: callback для кнопки "Назад"
    :param show_back: показывать ли кнопку "Назад"
    """
    keyboard = []

    # Проверка на пустой список
    if not items:
        if show_back:
            keyboard.append([InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=back_callback
            )])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    # Рассчитываем общее количество страниц
    total_pages = math.ceil(len(items) / items_per_page)
    current_page = min(max(1, current_page), total_pages)

    # Определяем элементы для текущей страницы
    start_idx = (current_page - 1) * items_per_page
    page_items = items[start_idx:start_idx + items_per_page]

    # Добавляем кнопки элементов
    for item in page_items:
        if isinstance(item, tuple) and len(item) >= 2:  # Если item - кортеж с названием и id
            name, item_id = item[0], item[1]
            keyboard.append([InlineKeyboardButton(
                text=name,
                callback_data=f"{callback_prefix}:{item_id}"
            )])
        else:  # Если item - просто строка
            keyboard.append([InlineKeyboardButton(
                text=item,
                callback_data=f"{callback_prefix}:{item}"
            )])

    # Добавляем кнопки навигации
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"img_page:{callback_prefix}:{current_page - 1}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="img_noop"))

    nav_row.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="img_noop"
    ))

    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"img_page:{callback_prefix}:{current_page + 1}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="img_noop"))

    keyboard.append(nav_row)

    # Добавляем кнопку "Назад"
    if show_back:
        keyboard.append([InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=back_callback
        )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_image_categories_keyboard(categories=None, current_page=1):
    """Создает пагинированную клавиатуру для выбора категорий при загрузке изображений"""
    if categories is None:
        from database.admins.image_db import get_categories
        categories = get_categories()

    return create_paginated_keyboard(
        categories,
        current_page=current_page,
        callback_prefix="img_category",
        back_callback="cancel_image_upload"
    )


def get_image_product_names_keyboard(product_names, category_name, current_page=1):
    """Создает пагинированную клавиатуру для выбора товаров при загрузке изображений"""
    return create_paginated_keyboard(
        product_names,
        current_page=current_page,
        callback_prefix=f"img_product",
        back_callback="back_to_image_categories"
    )
