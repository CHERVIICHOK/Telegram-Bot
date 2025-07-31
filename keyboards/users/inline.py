from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import math
from utils.catalog_mapping import catalog_mapping


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
            callback_data=f"page:{callback_prefix}:{current_page - 1}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    nav_row.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="noop"
    ))

    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"page:{callback_prefix}:{current_page + 1}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    keyboard.append(nav_row)

    # Добавляем кнопку "Назад"
    if show_back:
        keyboard.append([InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=back_callback
        )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_cart_keyboard(current_quantity, current_index, total_items, stock_quantity, product_id):
    """Создает клавиатуру для управления товаром в корзине"""
    keyboard = []

    # Первый ряд: управление количеством
    quantity_row = [
        InlineKeyboardButton(text="➖", callback_data=f"cart:dec:{product_id}"),
        InlineKeyboardButton(text=f"{current_quantity}", callback_data="no_action"),
        InlineKeyboardButton(
            text="➕" if current_quantity < stock_quantity else "",
            callback_data=f"cart:inc:{product_id}" if current_quantity < stock_quantity else "no_action"
        )
    ]
    keyboard.append(quantity_row)
    # Второй ряд: навигация по корзине
    navigation_row = [
        InlineKeyboardButton(
            text="⬅️" if current_index > 0 else " ",
            callback_data="cart:prev" if current_index > 0 else "no_action"
        ),
        InlineKeyboardButton(
            text="🗑️ Удалить товар",
            callback_data=f"cart:del:{product_id}"
        ),
        InlineKeyboardButton(
            text="➡️" if current_index < total_items - 1 else " ",
            callback_data="cart:next" if current_index < total_items - 1 else "no_action"
        )
    ]
    keyboard.append(navigation_row)

    # Третий ряд: навигация по боту
    keyboard.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="cart:main_menu"),
        InlineKeyboardButton(text="🛍️ К покупкам", callback_data="cart:catalog")
    ])

    # Четвертый ряд: оформление
    keyboard.append([
        InlineKeyboardButton(text="📝 Перейти к оформлению", callback_data="cart:checkout")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Клавиатура проверки возраста
def get_age_verification_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, мне есть 18 лет", callback_data="age_verify_yes")
    builder.button(text="Нет, мне нет 18 лет", callback_data="age_verify_no")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура выбора типа доставки
def get_delivery_type_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Самовывоз", callback_data="delivery_type_pickup")
    builder.button(text="Курьером", callback_data="delivery_type_courier")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура выбора способа оплаты
def get_payment_method_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Перевод", callback_data="payment_transfer")
    builder.button(text="Наличные при получении", callback_data="payment_cash")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура подтверждения заказа
def get_order_confirmation_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить заказ", callback_data="confirm_order")
    builder.button(text="Изменить данные", callback_data="edit_order")
    builder.button(text="Отменить заказ", callback_data="cancel_order")
    builder.adjust(1)
    return builder.as_markup()


# Генерация вариантов даты доставки (следующие 7 дней)
def get_delivery_date_kb():
    builder = InlineKeyboardBuilder()
    today = datetime.now()

    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
        display_text = f"{date_str} ({weekday})"
        builder.button(text=display_text, callback_data=f"date_{date_str}")

    builder.adjust(1)
    return builder.as_markup()


# Генерация временных слотов доставки
def get_delivery_time_kb():
    builder = InlineKeyboardBuilder()
    time_slots = [
        "10:00 - 12:00",
        "12:00 - 14:00",
        "14:00 - 16:00",
        "16:00 - 18:00",
        "18:00 - 20:00"
    ]

    for slot in time_slots:
        builder.button(text=slot, callback_data=f"time_{slot}")

    builder.adjust(1)
    return builder.as_markup()


# Клавиатура пропуска комментария
def get_skip_comment_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="skip_comment")
    return builder.as_markup()


def get_categories_keyboard(categories=None, current_page=1):
    """Создает пагинированную клавиатуру для выбора категорий"""
    if categories is None:
        from database.users.warehouse_connection import fetch_categories
        categories = fetch_categories()

    # Преобразуем названия в ID для callback_data
    items_with_ids = []
    for category in categories:
        cat_id = catalog_mapping.get_category_id(category)
        items_with_ids.append((category, cat_id))

    return create_paginated_keyboard_with_ids(
        items_with_ids,
        current_page=current_page,
        callback_prefix="category",
        back_callback="cancel_catalog"
    )


def get_product_names_keyboard(product_names, category_name, current_page=1):
    """Создает пагинированную клавиатуру для выбора подкатегорий товаров"""
    # Получаем ID категории
    cat_id = catalog_mapping.get_category_id(category_name)

    # Преобразуем названия товаров в ID
    items_with_ids = []
    for product_name in product_names:
        prod_id = catalog_mapping.get_product_id(category_name, product_name)
        items_with_ids.append((product_name, prod_id))

    return create_paginated_keyboard_with_ids(
        items_with_ids,
        current_page=current_page,
        callback_prefix=f"product_name:{cat_id}",
        back_callback="cancel_category_selection"
    )


def create_paginated_keyboard_with_ids(
        items_with_ids,
        current_page=1,
        items_per_page=7,
        callback_prefix="item",
        back_callback="back",
        page_callback_prefix="page"
):
    """Создает пагинированную клавиатуру с использованием ID"""
    total_pages = (len(items_with_ids) + items_per_page - 1) // items_per_page
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(items_with_ids))

    keyboard = InlineKeyboardBuilder()

    # Добавляем кнопки элементов
    for display_name, item_id in items_with_ids[start_idx:end_idx]:
        keyboard.button(
            text=display_name,
            callback_data=f"{callback_prefix}:{item_id}"
        )

    keyboard.adjust(1)

    # Навигация по страницам
    if total_pages > 1:
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"{page_callback_prefix}:{callback_prefix}:{current_page - 1}"
            ))

        nav_buttons.append(InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="noop"
        ))

        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"{page_callback_prefix}:{callback_prefix}:{current_page + 1}"
            ))

        keyboard.row(*nav_buttons)

    # Кнопка "Назад"
    keyboard.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=back_callback
    ))

    return keyboard.as_markup()


def get_flavors_keyboard(products, category_name, product_name):
    """Создает инлайн клавиатуру с вкусами товаров"""
    keyboard = InlineKeyboardBuilder()

    # Получаем ID для категории и товара
    cat_id = catalog_mapping.get_category_id(category_name)
    prod_id = catalog_mapping.get_product_id(category_name, product_name)

    # Добавляем кнопки с вкусами и ценами
    for product in products:
        product_full_name, flavor, price, product_id, description, quantity, image_path = product
        button_text = f"{flavor} - {price} руб."
        keyboard.button(
            text=button_text,
            callback_data=f"select_flavor:{product_id}"
        )

    # Размещаем кнопки в 1 столбец
    keyboard.adjust(1)

    # Добавляем кнопку возврата назад
    keyboard.row(
        InlineKeyboardButton(
            text="⬅️ Назад к подкатегориям",
            callback_data=f"back_to_products:{cat_id}:{prod_id}"
        )
    )

    # Добавляем кнопку отмены
    keyboard.row(
        InlineKeyboardButton(
            text="Вернуться в главное меню",
            callback_data="cancel_catalog"
        )
    )

    return keyboard.as_markup()


def get_flavor_actions_keyboard(product_id: int, category_name: str, product_name: str):
    # Получаем ID для категории и товара
    cat_id = catalog_mapping.get_category_id(category_name)
    prod_id = catalog_mapping.get_product_id(category_name, product_name)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 В корзину", callback_data=f"flavor_action:add_cart:{product_id}"),
        InlineKeyboardButton(text="❤️ В избранное", callback_data=f"flavor_action:add_fav:{product_id}")
    )
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад к выбору вкуса",
        callback_data=f"flavor_action:back_flavors:{cat_id}:{prod_id}"
    ))
    return builder.as_markup()


def get_product_details_keyboard(product_id, category_name, product_name, current_idx=0, total_products=1):
    """Создает клавиатуру для детального просмотра товара с пагинацией"""
    # Получаем ID для категории и товара
    cat_id = catalog_mapping.get_category_id(category_name)
    prod_id = catalog_mapping.get_product_id(category_name, product_name)

    keyboard = []

    # Навигационные кнопки
    nav_row = []
    if current_idx > 0:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"product_nav:{cat_id}:{prod_id}:{current_idx - 1}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    nav_row.append(InlineKeyboardButton(
        text=f"{current_idx + 1}/{total_products}",
        callback_data="noop"
    ))

    if current_idx < total_products - 1:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"product_nav:{cat_id}:{prod_id}:{current_idx + 1}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    keyboard.append(nav_row)

    # Кнопка добавления в корзину
    keyboard.append([InlineKeyboardButton(
        text="🛒 Добавить в корзину",
        callback_data=f"add_to_cart:{product_id}"
    )])

    # Кнопки навигации по меню
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 К списку товаров",
            callback_data=f"back_to_products:{cat_id}:{prod_id}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔝 К категориям",
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