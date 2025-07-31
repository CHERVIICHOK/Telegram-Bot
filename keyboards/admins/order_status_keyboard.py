from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import math
from utils.status_utils import ORDER_STATUS, STATUS_CATEGORIES


def get_status_emoji(status_key):
    """
    Возвращает эмодзи для статуса заказа
    Args:
        status_key: Ключ статуса заказа
    Returns:
        Эмодзи, соответствующее статусу
    """
    emojis = {
        "processing": "⏳",
        "confirmed": "🗳️",
        "assembly": "📦",
        "courier": "📫",
        "shipped": "🚚",
        "delivered": "✅",
        "canceled": "❌"
    }
    return emojis.get(status_key, "🔔")


def get_status_category_keyboard():
    """
    Создает клавиатуру для выбора категории статусов заказов.
    Returns:
        InlineKeyboardMarkup с кнопками категорий статусов
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для каждой категории статусов
    for category_key, category_info in STATUS_CATEGORIES.items():
        builder.add(InlineKeyboardButton(
            text=f"{category_info['emoji']} {category_info['name']}",
            callback_data=f"status_category:{category_key}"
        ))

    builder.adjust(1)  # По одной кнопке в ряду

    # Добавляем кнопку возврата в главное меню
    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="admin_menu"
    ))

    return builder.as_markup()


def get_orders_keyboard(orders, page, total_orders, per_page=7, category_key=None):
    """
    Создает клавиатуру с пагинацией для списка заказов.
    Args:
        orders: Список заказов
        page: Текущая страница
        total_orders: Общее количество заказов
        per_page: Количество заказов на странице
        category_key: Ключ категории статусов (если есть)
    Returns:
        InlineKeyboardMarkup с кнопками заказов и навигации
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для каждого заказа с эмодзи статуса
    for order in orders:
        status_key = order['status']
        status_text = ORDER_STATUS.get(status_key, "Неизвестный статус")
        emoji = get_status_emoji(status_key)
        button_text = f"{emoji} Заказ #{order['id']} - {status_text}"
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"order_status:{order['id']}"
        ))

    builder.adjust(1)  # По одной кнопке в ряду

    # Добавляем навигационные кнопки
    navigation_row = []
    total_pages = math.ceil(total_orders / per_page) if total_orders > 0 else 1

    if page > 1:
        callback_data = f"order_list:{page - 1}"
        if category_key:
            callback_data = f"cat_order_list:{category_key}:{page - 1}"

        navigation_row.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=callback_data
        ))

    navigation_row.append(InlineKeyboardButton(
        text=f"📄 {page}/{total_pages}",
        callback_data="ignore"
    ))

    if page < total_pages:
        callback_data = f"order_list:{page + 1}"
        if category_key:
            callback_data = f"cat_order_list:{category_key}:{page + 1}"

        navigation_row.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=callback_data
        ))

    builder.row(*navigation_row)

    # Добавляем кнопки навигации между интерфейсами
    back_button = InlineKeyboardButton(
        text="🔙 К категориям",
        callback_data="back_to_categories"
    ) if category_key else None

    menu_button = InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="admin_menu"
    )

    if back_button:
        builder.row(back_button, menu_button)
    else:
        builder.row(menu_button)

    return builder.as_markup()


def get_order_status_keyboard(order_id):
    """
    Создает клавиатуру для выбора статуса заказа.

    Args:
        order_id: ID заказа

    Returns:
        InlineKeyboardMarkup с кнопками статусов и навигации
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для каждого статуса с эмодзи
    for status_key, status_text in ORDER_STATUS.items():
        emoji = get_status_emoji(status_key)
        builder.add(InlineKeyboardButton(
            text=f"{emoji} {status_text}",
            callback_data=f"set_status:{order_id}:{status_key}"
        ))

    builder.adjust(1)  # По одной кнопке в ряду

    # Добавляем кнопку удаления заказа в отдельном ряду
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить заказ",
            callback_data=f"delete_order:{order_id}"
        )
    )

    # Добавляем кнопки навигации
    builder.row(
        InlineKeyboardButton(
            text="🔙 К списку заказов",
            callback_data="back_to_orders"
        ),
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="admin_menu"
        )
    )

    return builder.as_markup()


def get_confirm_delete_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"cancel_delete_order:{order_id}"
                ),
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"confirm_delete_order:{order_id}"
                ),
            ]
        ]
    )