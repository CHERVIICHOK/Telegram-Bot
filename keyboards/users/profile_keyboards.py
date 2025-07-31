from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.users.database import get_special_user_id
from utils.status_utils import ORDER_STATUS


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для главного меню личного кабинета"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🔍 Отследить заказ",
        callback_data="profile:track_orders"
    ))

    builder.row(InlineKeyboardButton(
        text="📋 История заказов",
        callback_data="profile:order_history"
    ))

    # Новая кнопка для предзаказов
    builder.row(InlineKeyboardButton(
        text="🛍️ Товары скоро в продаже",
        callback_data="profile:preorders"
    ))

    builder.row(InlineKeyboardButton(
        text="📦 Мои предзаказы",
        callback_data="profile:my_preorders"
    ))

    builder.row(InlineKeyboardButton(
        text="❤️ Избранное",
        callback_data="profile:favorites"
    ))

    builder.row(InlineKeyboardButton(
        text="📝 О себе",
        callback_data="profile:about_me"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Вернуться в главное меню",
        callback_data="profile:back_to_main"
    ))

    return builder.as_markup()


def get_active_order_list_keyboard(orders, prefix="track") -> InlineKeyboardMarkup:
    """Клавиатура для списка активных заказов (не доставленных)"""
    builder = InlineKeyboardBuilder()

    active_orders = [order for order in orders if order[1] != "delivered"]

    for order in active_orders:
        order_id, status, date = order
        emoji = get_status_emoji(status)

        status_text = ORDER_STATUS.get(status, "Неизвестный статус")

        date_str = date.split()[0] if ' ' in date else date

        builder.row(InlineKeyboardButton(
            text=f"{emoji} Заказ #{get_special_user_id(order_id)} от {date_str} - {status_text}",
            callback_data=f"profile:{prefix}_order_{order_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="profile:back_to_profile"
    ))

    return builder.as_markup()


def get_delivered_order_list_keyboard(orders, prefix="history") -> InlineKeyboardMarkup:
    """Клавиатура для списка доставленных заказов"""
    builder = InlineKeyboardBuilder()

    delivered_orders = [order for order in orders if order[1] == "delivered"]

    for order in delivered_orders:
        id, status, date, user_order_id = order
        emoji = get_status_emoji(status)

        status_text = ORDER_STATUS.get(status, "Неизвестный статус")

        date_str = date.split()[0] if ' ' in date else date

        builder.row(InlineKeyboardButton(
            text=f"{emoji} Заказ #{user_order_id} от {date_str} - {status_text}",
            callback_data=f"profile:{prefix}_order_{id}"  # Важно, чтобы тут был order_id, а не user_order_id
        ))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="profile:back_to_profile"
    ))

    return builder.as_markup()


def get_order_list_keyboard(orders, prefix="track") -> InlineKeyboardMarkup:
    """Клавиатура для списка заказов"""
    builder = InlineKeyboardBuilder()

    for order in orders:
        order_id, status, date = order
        emoji = get_status_emoji(status)

        status_text = ORDER_STATUS.get(status, "Неизвестный статус")

        date_str = date.split()[0] if ' ' in date else date

        builder.row(InlineKeyboardButton(
            text=f"{emoji} Заказ #{order_id} от {date_str} - {status_text}",
            callback_data=f"profile:{prefix}_order_{order_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="profile:back_to_profile"
    ))

    return builder.as_markup()


def get_active_order_detail_keyboard(order_id, user_order_id, is_active=True, can_cancel=False) -> InlineKeyboardMarkup:
    """Клавиатура для деталей активного заказа"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📞 Связаться с поддержкой",
        callback_data=f"profile:support_{user_order_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔄 Повторить заказ",
        callback_data=f"profile:repeat_order_{order_id}"
    ))

    if can_cancel and is_active:
        builder.row(InlineKeyboardButton(
            text="❌ Отказаться от заказа",
            callback_data=f"profile:cancel_order_{order_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад к списку",
        callback_data="profile:back_to_orders"
    ))

    return builder.as_markup()


def get_delivered_order_detail_keyboard(order_id, user_order_id, delivery_rated=False,
                                        products_rated=False) -> InlineKeyboardMarkup:
    """Клавиатура для деталей завершенного заказа"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📞 Связаться с поддержкой",
        callback_data=f"profile:support_{user_order_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔄 Повторить заказ",
        callback_data=f"profile:repeat_order_{order_id}"
    ))

    if not delivery_rated:
        builder.row(InlineKeyboardButton(
            text="⭐ Оценить доставку",
            callback_data=f"profile:rate_delivery_{order_id}"
        ))

    if not products_rated:
        builder.row(InlineKeyboardButton(
            text="✅ Оценить товары",
            callback_data=f"profile:rate_product_list_{order_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад к списку",
        callback_data="profile:back_to_orders"
    ))

    return builder.as_markup()


def get_order_detail_keyboard(order_id, is_active=True, can_cancel=False, delivery_rated=False,
                              products_rated=False) -> InlineKeyboardMarkup:
    """Клавиатура для деталей заказа"""
    builder = InlineKeyboardBuilder()

    if is_active:
        builder.row(InlineKeyboardButton(
            text="📞 Связаться с поддержкой",
            callback_data=f"profile:support_{order_id}"
        ))

    if can_cancel:
        builder.row(InlineKeyboardButton(
            text="❌ Отказаться от заказа",
            callback_data=f"profile:cancel_order_{order_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="🔄 Повторить заказ",
        callback_data=f"profile:repeat_order_{order_id}"
    ))

    if not delivery_rated:
        builder.row(InlineKeyboardButton(
            text="⭐ Оценить доставку",
            callback_data=f"profile:rate_delivery_{order_id}"
        ))
    else:
        builder.row(InlineKeyboardButton(text="Спасибо за оценку доставки!"))

    if not products_rated:
        builder.row(InlineKeyboardButton(
            text="✅ Оценить товары",
            callback_data=f"profile:rate_product_list_{order_id}"
        ))
    else:
        builder.row(InlineKeyboardButton(text="Спасибо за оценку товаров!"))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад к списку",
        callback_data="profile:back_to_orders"
    ))

    return builder.as_markup()


def get_delivery_rating_keyboard(order_id) -> InlineKeyboardMarkup:
    """Клавиатура для оценки доставки"""
    builder = InlineKeyboardBuilder()

    # Первая строка
    builder.row(InlineKeyboardButton(
        text="⭐⭐⭐⭐⭐",
        callback_data=f"profile:delivery_rating_{order_id}_{5}"
    ),
        InlineKeyboardButton(
            text="⭐⭐⭐⭐",
            callback_data=f"profile:delivery_rating_{order_id}_{4}"
        )
    )

    # Третья строка
    builder.row(
        InlineKeyboardButton(
            text="⭐⭐⭐",
            callback_data=f"profile:delivery_rating_{order_id}_{3}"
        ),
        InlineKeyboardButton(
            text="⭐⭐",
            callback_data=f"profile:delivery_rating_{order_id}_{2}"
        ),
        InlineKeyboardButton(
            text="⭐",
            callback_data=f"profile:delivery_rating_{order_id}_{1}"
        )
    )

    builder.row(InlineKeyboardButton(
        text="↩️ Отменить и вернуться в профиль",
        callback_data="profile:back_to_orders"
    ))

    return builder.as_markup()


def get_product_rating_keyboard(order_id, product_id) -> InlineKeyboardMarkup:
    """Клавиатура для оценки товара"""
    builder = InlineKeyboardBuilder()

    # Первая строка
    builder.row(
        InlineKeyboardButton(
            text="⭐⭐⭐⭐⭐",
            callback_data=f"profile:product_rating_{order_id}_{product_id}_{5}"
        ),
        InlineKeyboardButton(
            text="⭐⭐⭐⭐",
            callback_data=f"profile:product_rating_{order_id}_{product_id}_{4}"
        )
    )

    # Третья строка
    builder.row(
        InlineKeyboardButton(
            text="⭐⭐⭐",
            callback_data=f"profile:product_rating_{order_id}_{product_id}_{3}"
        ),
        InlineKeyboardButton(
            text="⭐⭐",
            callback_data=f"profile:product_rating_{order_id}_{product_id}_{2}"
        ),
        InlineKeyboardButton(
            text="⭐",
            callback_data=f"profile:product_rating_{order_id}_{product_id}_{1}"
        )
    )

    builder.row(InlineKeyboardButton(
        text="↩️ Отменить и вернуться к списку товаров",
        callback_data=f"profile:rate_product_list_{order_id}"
    ))

    return builder.as_markup()


def get_product_list_keyboard(order_id, product_details) -> InlineKeyboardMarkup:
    """Клавиатура для списка товаров для оценки"""
    builder = InlineKeyboardBuilder()
    for product in product_details:
        product_id = product['product_id']
        product_name = product['product_name']
        flavor = product['flavor']

        truncated_name = product_name[:15]
        truncated_flavor = flavor[:15]

        name_suffix = "..." if len(product_name) > 15 else ""
        flavor_suffix = "..." if len(flavor) > 15 else ""

        button_text = f"{truncated_name}{name_suffix} - {truncated_flavor}{flavor_suffix}"
        builder.row(InlineKeyboardButton(
            text=button_text,
            callback_data=f"profile:rate_product_{order_id}_{product_id}"
        ))
    builder.row(InlineKeyboardButton(
        text="↩️ Отменить и вернуться в профиль",
        callback_data="profile:back_to_orders"
    ))
    return builder.as_markup()


def get_comment_keyboard(skip_callback: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой "Пропустить"."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Пропустить",
            callback_data=skip_callback,
        )
    )
    return builder.as_markup()


def get_support_keyboard(order_id) -> InlineKeyboardMarkup:
    """Клавиатура для связи с поддержкой"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="📱 Связаться с оператором",
        url="https://t.me/zaxhz"
    ))

    builder.row(InlineKeyboardButton(
        text="↩️ Назад к заказу",
        callback_data=f"profile:back_to_order_{order_id}"
    ))

    return builder.as_markup()


def get_status_emoji(status):
    """Эмодзи для визуального отображения статуса заказа"""
    status_emojis = {
        "processing": "⏳",
        "confirmed": "🗳️",
        "assembly": "📦",
        "courier": "📫",
        "shipped": "🚚",
        "delivered": "✅",
        "canceled": "❌"
    }
    return status_emojis.get(status, "🔔")
