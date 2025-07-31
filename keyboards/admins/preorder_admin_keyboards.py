from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any


def get_preorder_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню управления предзаказами для админа"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="➕ Добавить товар",
        callback_data="preorder_admin:add"
    ))

    builder.row(InlineKeyboardButton(
        text="📤 Массовая загрузка (Excel)",
        callback_data="preorder_admin:bulk_upload"
    ))

    builder.row(InlineKeyboardButton(
        text="📋 Список товаров",
        callback_data="preorder_admin:list"
    ))

    builder.row(InlineKeyboardButton(
        text="📊 Статистика предзаказов",
        callback_data="preorder_admin:stats"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад в админ-меню",
        callback_data="admin:main"
    ))

    return builder.as_markup()


def get_preorder_products_list_keyboard(products: List[Dict[str, Any]],
                                        page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура со списком товаров для предзаказа с пагинацией"""
    builder = InlineKeyboardBuilder()

    for product in products:
        text = f"{product['category']} - {product['product_name']} ({product['flavor']})"
        if product.get('preorder_count', 0) > 0:
            text += f" [{product['preorder_count']} заказов]"

        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"preorder_admin:view:{product['id']}"
        ))

    # Кнопки пагинации
    if total_pages > 1:
        buttons = []
        if page > 1:
            buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"preorder_admin:list_page:{page - 1}"
            ))

        buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="preorder_admin:current_page"
        ))

        if page < total_pages:
            buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"preorder_admin:list_page:{page + 1}"
            ))

        builder.row(*buttons)

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="preorder_admin:menu"
    ))

    return builder.as_markup()


def get_product_admin_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления конкретным товаром"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🗑️ Удалить товар",
        callback_data=f"preorder_admin:delete:{product_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад к списку",
        callback_data="preorder_admin:list"
    ))

    return builder.as_markup()


def get_confirm_delete_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"preorder_admin:confirm_delete:{product_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"preorder_admin:view:{product_id}"
        )
    )

    return builder.as_markup()


def get_add_product_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены добавления товара"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="preorder_admin:cancel_add"
    ))

    return builder.as_markup()


def get_skip_step_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой пропуска шага"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⏭️ Пропустить",
            callback_data="preorder_admin:skip_step"
        ),
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="preorder_admin:cancel_add"
        )
    )

    return builder.as_markup()


def get_category_selection_keyboard(categories: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура для быстрого выбора существующей категории"""
    builder = InlineKeyboardBuilder()

    for category in categories[:10]:  # Ограничиваем количество кнопок
        builder.row(InlineKeyboardButton(
            text=f"📦 {category}",
            callback_data=f"preorder_admin:select_category:{category}"
        ))

    builder.row(InlineKeyboardButton(
        text="✏️ Ввести новую категорию",
        callback_data="preorder_admin:new_category"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="preorder_admin:cancel_add"
    ))

    return builder.as_markup()


def get_product_name_selection_keyboard(product_names: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура для быстрого выбора существующего названия товара"""
    builder = InlineKeyboardBuilder()

    for name in product_names[:10]:  # Ограничиваем количество кнопок
        builder.row(InlineKeyboardButton(
            text=f"🛍️ {name}",
            callback_data=f"preorder_admin:select_product:{name}"
        ))

    builder.row(InlineKeyboardButton(
        text="✏️ Ввести новое название",
        callback_data="preorder_admin:new_product"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="preorder_admin:cancel_add"
    ))

    return builder.as_markup()


def get_confirm_add_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения добавления товара"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data="preorder_admin:confirm_add"
        ),
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data="preorder_admin:edit_summary"
        )
    )

    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="preorder_admin:cancel_add"
    ))

    return builder.as_markup()


def get_edit_field_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора поля для редактирования"""
    builder = InlineKeyboardBuilder()

    fields = [
        ("📦 Категория", "category"),
        ("🛍️ Название", "product_name"),
        ("🍓 Вкус", "flavor"),
        ("📝 Описание", "description"),
        ("💰 Цена", "price"),
        ("📅 Дата поставки", "expected_date"),
        ("🖼️ Изображение", "image")
    ]

    for text, field in fields:
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"preorder_admin:edit:{field}"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад к подтверждению",
        callback_data="preorder_admin:back_to_confirm"
    ))

    return builder.as_markup()


def get_stats_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для статистики с пагинацией"""
    builder = InlineKeyboardBuilder()

    # Кнопки пагинации
    if total_pages > 1:
        buttons = []
        if page > 1:
            buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"preorder_admin:stats_page:{page - 1}"
            ))

        buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="preorder_admin:current_stats_page"
        ))

        if page < total_pages:
            buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"preorder_admin:stats_page:{page + 1}"
            ))

        builder.row(*buttons)

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="preorder_admin:menu"
    ))

    return builder.as_markup()


def get_bulk_upload_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для массовой загрузки"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📥 Скачать шаблон Excel",
        callback_data="preorder_admin:download_template"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="preorder_admin:cancel_bulk"
    ))

    return builder.as_markup()


def get_bulk_upload_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения массовой загрузки"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Загрузить товары",
            callback_data="preorder_admin:confirm_bulk"
        ),
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="preorder_admin:cancel_bulk"
        )
    )

    return builder.as_markup()
