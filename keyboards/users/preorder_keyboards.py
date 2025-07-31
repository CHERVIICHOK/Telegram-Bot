from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any


def get_preorder_categories_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура с категориями товаров для предзаказа"""
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.row(InlineKeyboardButton(
            text=f"📦 {category['name']}",
            callback_data=f"po:c:{category['id']}"  # po = preorder, c = category
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад в личный кабинет",
        callback_data="profile:main"
    ))

    return builder.as_markup()


def get_preorder_products_keyboard(category_id: int, products: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура с товарами в категории"""
    builder = InlineKeyboardBuilder()

    for product in products:
        builder.row(InlineKeyboardButton(
            text=f"🛍️ {product['name']}",
            callback_data=f"po:p:{category_id}:{product['id']}"  # p = product
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад к категориям",
        callback_data="po:main"
    ))

    return builder.as_markup()


def get_preorder_flavors_keyboard(category_id: int, product_id: int,
                                  flavors: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура с вкусами товара"""
    builder = InlineKeyboardBuilder()

    for flavor in flavors:
        builder.row(InlineKeyboardButton(
            text=f"🍓 {flavor['flavor']}",
            callback_data=f"po:f:{flavor['id']}"  # f = flavor, используем ID конкретного товара
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад к товарам",
        callback_data=f"po:c:{category_id}"
    ))

    return builder.as_markup()


def get_product_card_keyboard(product_id: int, has_preorder: bool,
                              category_id: int, parent_product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для карточки товара"""
    builder = InlineKeyboardBuilder()

    if has_preorder:
        builder.row(InlineKeyboardButton(
            text="❌ Отменить предзаказ",
            callback_data=f"po:cancel:{product_id}"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="✅ Сделать предзаказ",
            callback_data=f"po:make:{product_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад к вкусам",
        callback_data=f"po:p:{category_id}:{parent_product_id}"
    ))

    return builder.as_markup()


def get_my_preorders_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка предзаказов пользователя с пагинацией"""
    builder = InlineKeyboardBuilder()

    # Кнопки пагинации
    if total_pages > 1:
        buttons = []
        if page > 1:
            buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"po:my:page:{page - 1}"
            ))

        buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="po:my:current"
        ))

        if page < total_pages:
            buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"po:my:page:{page + 1}"
            ))

        builder.row(*buttons)

    builder.row(InlineKeyboardButton(
        text="🔙 Назад в личный кабинет",
        callback_data="profile:main"
    ))

    return builder.as_markup()


def get_cancellation_reason_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора причины отказа"""
    builder = InlineKeyboardBuilder()

    reasons = [
        ("💰 Изменились финансовые обстоятельства", "financial"),
        ("⏰ Слишком долго ждать", "too_long"),
        ("🔄 Нашёл в другом месте", "found_elsewhere"),
        ("❌ Передумал", "changed_mind"),
        ("📝 Другая причина", "other")
    ]

    for text, reason_code in reasons:
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"po:reason:{reason_code}"
        ))

    builder.row(InlineKeyboardButton(
        text="🔙 Отмена",
        callback_data="po:cancel_reason"
    ))

    return builder.as_markup()


def get_back_to_card_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для возврата к карточке товара"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🔙 Вернуться к товару",
        callback_data=f"po:f:{product_id}"
    ))

    return builder.as_markup()
