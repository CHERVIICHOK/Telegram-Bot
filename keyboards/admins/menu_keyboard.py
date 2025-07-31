from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_menu_keyboard():
    """
    Создает клавиатуру главного меню администратора.
    Returns InlineKeyboardMarkup с кнопками административных функций
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="🎁 Управление скидками", callback_data="admin_discounts_menu"),
        InlineKeyboardButton(text="📊 Изменить статус заказа", callback_data="cmd_change_order_status"),
        InlineKeyboardButton(text="📦 Управление товарами", callback_data="manage_products"),
        # InlineKeyboardButton(text="🛒 Обработать заказ", callback_data="process_order"),
        InlineKeyboardButton(text="👥 Управление персоналом", callback_data="manage_staff"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="admin_statistics"),
        InlineKeyboardButton(text="💬 Связь с клиентом", callback_data="client_contact"),
        InlineKeyboardButton(text="📨 Рассылка", callback_data="send_broadcast"),
        InlineKeyboardButton(text="⏱️ Время обработки заказов", callback_data="timeout_settings"),
        InlineKeyboardButton(text="🛍️ Управление предзаказами", callback_data="manage_preorders"),
        InlineKeyboardButton(text="🖼️ Добавить изображение товара", callback_data="add_product_image"),
        InlineKeyboardButton(text="🔔 Уведомления о низком остатке", callback_data="manage_stock_thresholds"),
        # InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )

    builder.adjust(1)

    return builder.as_markup()


def get_courier_menu_keyboard():
    """
    Создает клавиатуру главного меню курьера.
    Returns InlineKeyboardMarkup с кнопками курьерских функций
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📊 Изменить статус заказа", callback_data="cmd_change_order_status"),
        InlineKeyboardButton(text="🖼️ Добавить изображение товара", callback_data="add_product_image"),
    )

    builder.adjust(1)

    return builder.as_markup()
