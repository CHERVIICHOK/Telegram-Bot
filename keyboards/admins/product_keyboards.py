from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_products_menu_keyboard():
    """Создает основную клавиатуру меню управления товарами."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📋 Просмотр товаров", callback_data="view_products"),
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product"),
        InlineKeyboardButton(text="🗂 Управление категориями", callback_data="manage_categories"),
        InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data="back_to_admin_menu")
    )

    builder.adjust(1)
    return builder.as_markup()


def get_category_selection_keyboard(categories, action="view", page=1, total_pages=1):
    """Создает клавиатуру выбора категории с пагинацией."""
    builder = InlineKeyboardBuilder()

    # Добавляем кнопку "Все товары" для просмотра
    if action == "view":
        builder.add(InlineKeyboardButton(
            text="🔍 Все товары",
            callback_data=f"view_category:all:{page}"
        ))

    # Добавляем кнопки категорий
    for category in categories:
        if action == "view":
            callback_data = f"view_category:{category}:{page}"
        elif action == "edit":
            callback_data = f"edit_category:{category}"
        elif action == "delete":
            callback_data = f"delete_category:{category}"
        else:
            callback_data = f"select_category:{category}"

        builder.add(InlineKeyboardButton(
            text=category,
            callback_data=callback_data
        ))

    # Добавляем навигационные кнопки
    nav_buttons = []

    if page > 1:
        prev_page = page - 1
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"category_page:{action}:{prev_page}"
        ))

    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="ignored"
        ))

    if page < total_pages:
        next_page = page + 1
        nav_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"category_page:{action}:{next_page}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_products_menu"
    ))

    builder.adjust(1)
    return builder.as_markup()


def get_products_list_keyboard(products, category=None, page=1, total_pages=1):
    """Создает клавиатуру списка товаров с пагинацией."""
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки товаров
    for product in products:
        product_id = product[0]
        product_name = product[3]  # product_full_name
        quantity = product[7]

        builder.add(InlineKeyboardButton(
            text=f"{product_name} (остаток: {quantity})",
            callback_data=f"product_details:{product_id}"
        ))

    # Добавляем навигационные кнопки
    nav_buttons = []

    if page > 1:
        prev_page = page - 1
        category_param = f":{category}" if category else ":all"
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"products_page:{prev_page}{category_param}"
        ))

    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="ignored"
        ))

    if page < total_pages:
        next_page = page + 1
        category_param = f":{category}" if category else ":all"
        nav_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"products_page:{next_page}{category_param}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(
        text="↩️ Назад к категориям",
        callback_data="back_to_categories"
    ))

    builder.adjust(1)
    return builder.as_markup()


def get_product_details_keyboard(product_id, is_active=True):
    """Создает клавиатуру для просмотра деталей товара и действий с ним."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"edit_product:{product_id}"
        ),
        InlineKeyboardButton(
            text="❌ Деактивировать" if is_active else "✅ Активировать",
            callback_data=f"toggle_product:{product_id}:{0 if is_active else 1}"
        ),
        InlineKeyboardButton(
            text="↩️ Назад к списку",
            callback_data="back_to_products_list"
        )
    )

    builder.adjust(1)
    return builder.as_markup()


def get_edit_product_keyboard(product_id):
    """Создает клавиатуру для выбора параметра товара для редактирования."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="🔤 Категория",
            callback_data=f"edit_product_field:{product_id}:category"
        ),
        InlineKeyboardButton(
            text="📝 Название",
            callback_data=f"edit_product_field:{product_id}:product_name"
        ),
        InlineKeyboardButton(
            text="🍬 Вкус",
            callback_data=f"edit_product_field:{product_id}:flavor"
        ),
        InlineKeyboardButton(
            text="💰 Цена",
            callback_data=f"edit_product_field:{product_id}:price"
        ),
        InlineKeyboardButton(
            text="📋 Описание",
            callback_data=f"edit_product_field:{product_id}:description"
        ),
        InlineKeyboardButton(
            text="🔢 Количество",
            callback_data=f"edit_product_field:{product_id}:quantity"
        ),
        InlineKeyboardButton(
            text="🖼 Изображение",
            callback_data=f"edit_product_field:{product_id}:image_path"
        ),
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data=f"product_details:{product_id}"
        )
    )

    builder.adjust(1)
    return builder.as_markup()


def get_categories_management_keyboard():
    """Создает клавиатуру для управления категориями."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="➕ Добавить категорию",
            callback_data="add_category"
        ),
        InlineKeyboardButton(
            text="✏️ Редактировать категорию",
            callback_data="edit_categories"
        ),
        InlineKeyboardButton(
            text="❌ Удалить категорию",
            callback_data="delete_categories"
        ),
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data="back_to_products_menu"
        )
    )

    builder.adjust(1)
    return builder.as_markup()


def get_confirm_cancel_keyboard(action, item_id=None):
    """Создает клавиатуру с кнопками подтверждения и отмены."""
    builder = InlineKeyboardBuilder()

    confirm_data = f"confirm_{action}"
    if item_id:
        confirm_data += f":{item_id}"

    cancel_data = f"cancel_{action}"
    if item_id:
        cancel_data += f":{item_id}"

    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_data)
    )

    builder.adjust(2)
    return builder.as_markup()


def get_back_keyboard(callback_data="back_to_products_menu"):
    """Создает простую клавиатуру с кнопкой "Назад"."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data=callback_data))
    return builder.as_markup()