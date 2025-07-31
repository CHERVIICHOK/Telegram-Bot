from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Tuple


def get_stock_threshold_menu_keyboard():
    """
    Создает клавиатуру меню настройки порогов уведомлений
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📊 Установить порог для товара", callback_data="set_product_threshold"),
        InlineKeyboardButton(text="📋 Просмотреть установленные пороги", callback_data="view_thresholds"),
        InlineKeyboardButton(text="📢 Проверить товары с низким остатком", callback_data="check_low_stock"),
        InlineKeyboardButton(text="📜 Журнал уведомлений", callback_data="view_notification_log"),
        InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_admin_menu")
    )

    builder.adjust(1)  # По одной кнопке в ряду

    return builder.as_markup()


def get_categories_for_threshold_keyboard(categories: List[str]):
    """
    Создает клавиатуру с категориями товаров для выбора при настройке порогов
    """
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.add(InlineKeyboardButton(
            text=category,
            callback_data=f"threshold_category:{category}"
        ))

    builder.add(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="back_to_threshold_menu"
    ))

    builder.adjust(1)  # По одной кнопке в ряду

    return builder.as_markup()


def get_products_for_threshold_keyboard(products: List[Tuple[int, str]], category: str):
    """
    Создает клавиатуру с товарами в выбранной категории
    """
    builder = InlineKeyboardBuilder()

    for product_id, product_name in products:
        builder.add(InlineKeyboardButton(
            text=product_name,
            callback_data=f"threshold_product:{product_id}"
        ))

    builder.add(InlineKeyboardButton(
        text="🔙 Назад к категориям",
        callback_data="back_to_threshold_categories"
    ))

    builder.adjust(1)  # По одной кнопке в ряду

    return builder.as_markup()


def get_threshold_confirmation_keyboard(product_id: int, threshold: int):
    """
    Создает клавиатуру подтверждения установки порога
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm_threshold:{product_id}:{threshold}"
        ),
        InlineKeyboardButton(
            text="🔄 Изменить",
            callback_data=f"change_threshold:{product_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_threshold_setting"
        )
    )

    builder.adjust(1)  # По одной кнопке в ряду

    return builder.as_markup()


def get_thresholds_list_keyboard(
        thresholds: List[Tuple[int, str, int, int]],
        page: int = 0,
        items_per_page: int = 5
):
    """
    Создает клавиатуру со списком установленных порогов уведомлений с пагинацией
    """
    builder = InlineKeyboardBuilder()

    # Вычисляем общее количество страниц
    total_pages = (len(thresholds) + items_per_page - 1) // items_per_page

    # Извлекаем элементы для текущей страницы
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(thresholds))
    current_items = thresholds[start_idx:end_idx]

    # Добавляем кнопки для каждого товара
    for product_id, product_name, threshold, stock in current_items:
        builder.add(InlineKeyboardButton(
            text=f"{product_name} ({stock}/{threshold})",
            callback_data=f"edit_threshold:{product_id}"
        ))

    # Добавляем навигационные кнопки
    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"threshold_page:{page - 1}"
        ))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Вперед",
            callback_data=f"threshold_page:{page + 1}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.add(InlineKeyboardButton(
        text="🔙 В меню порогов",
        callback_data="back_to_threshold_menu"
    ))

    builder.adjust(1)  # По одной кнопке в ряду, кроме навигационных

    return builder.as_markup()


def get_notification_log_keyboard(page: int = 0):
    """
    Создает клавиатуру для просмотра журнала уведомлений
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="⬅️ Предыдущие",
            callback_data=f"notification_log_page:{page - 1}"
        ),
        InlineKeyboardButton(
            text="➡️ Следующие",
            callback_data=f"notification_log_page:{page + 1}"
        ),
        InlineKeyboardButton(
            text="🔙 В меню порогов",
            callback_data="back_to_threshold_menu"
        )
    )

    builder.adjust(2, 1)  # Две кнопки в первом ряду, одна во втором

    return builder.as_markup()
