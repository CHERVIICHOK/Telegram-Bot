from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_statistics_menu_keyboard():
    """
    Создает клавиатуру меню статистики для администратора.
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками статистики
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="💰 Рассчитать стоимость склада", callback_data="calculate_warehouse_value"),
        InlineKeyboardButton(text="📊 Статистика продаж", callback_data="sales_statistics"),
        InlineKeyboardButton(text="💹 Статистика прибыли", callback_data="profit_statistics"),
        InlineKeyboardButton(text="🔙 Вернуться в панель управления", callback_data="back_to_admin_menu"),
    )

    builder.adjust(1)

    return builder.as_markup()


def get_back_to_statistics_keyboard():
    """
    Создает клавиатуру с кнопкой возврата в меню статистики.
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="🔙 Вернуться в меню статистики", callback_data="back_to_statistics"),
    )

    return builder.as_markup()


def get_pagination_keyboard(current_page, total_pages, prefix):
    """
    Создает клавиатуру пагинации для просмотра статистики.

    Args:
        current_page (int): Текущая страница
        total_pages (int): Общее количество страниц
        prefix (str): Префикс для callback_data

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками навигации
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки навигации, если больше одной страницы
    if total_pages > 1:
        # Кнопка "Назад"
        if current_page > 1:
            builder.add(InlineKeyboardButton(
                text="◀️",
                callback_data=f"{prefix}_page_{current_page - 1}"
            ))

        # Информация о текущей странице
        builder.add(InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="current_page"
        ))

        # Кнопка "Вперед"
        if current_page < total_pages:
            builder.add(InlineKeyboardButton(
                text="▶️",
                callback_data=f"{prefix}_page_{current_page + 1}"
            ))

    # Кнопка возврата в меню статистики
    builder.add(InlineKeyboardButton(
        text="🔙 Вернуться в меню статистики",
        callback_data="back_to_statistics"
    ))

    # Регулировка расположения кнопок
    if total_pages > 1:
        builder.adjust(3, 1)  # 3 кнопки в первом ряду (навигация), 1 - во втором (возврат)
    else:
        builder.adjust(1)  # Только кнопка возврата

    return builder.as_markup()