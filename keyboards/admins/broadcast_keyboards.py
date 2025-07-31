from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional


def get_broadcast_menu_keyboard():
    """Создает основную клавиатуру меню рассылки."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📤 Создать рассылку", callback_data="create_broadcast"),
        # InlineKeyboardButton(text="📋 История рассылок", callback_data="broadcast_history"),
        # InlineKeyboardButton(text="📑 Шаблоны рассылок", callback_data="broadcast_templates"),
        InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data="back_to_admin_menu")
    )

    builder.adjust(1)
    return builder.as_markup()


def get_broadcast_type_keyboard():
    """Создает клавиатуру выбора типа рассылки."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="💬 Текстовое сообщение", callback_data="broadcast_type:text"),
        # InlineKeyboardButton(text="🖼 Сообщение с фото", callback_data="broadcast_type:photo"),
        # InlineKeyboardButton(text="📋 Использовать шаблон", callback_data="broadcast_use_template"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_broadcast_menu")
    )

    builder.adjust(1)
    return builder.as_markup()


def get_target_selection_keyboard():
    """Создает клавиатуру выбора целевой аудитории."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="👥 Все пользователи", callback_data="broadcast_target:all"),
        # InlineKeyboardButton(text="🔄 Активные пользователи", callback_data="broadcast_target:active"),
        # InlineKeyboardButton(text="🌍 По региону", callback_data="broadcast_target:region"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_broadcast_type")
    )

    builder.adjust(1)
    return builder.as_markup()


def get_time_selection_keyboard():
    """Создает клавиатуру выбора времени отправки."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="🚀 Отправить сейчас", callback_data="broadcast_time:now"),
        # InlineKeyboardButton(text="⏰ Запланировать", callback_data="broadcast_time:schedule"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_broadcast_target")
    )

    builder.adjust(1)
    return builder.as_markup()


def get_active_users_period_keyboard():
    """Создает клавиатуру выбора периода для активных пользователей."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="7 дней", callback_data="active_period:7"),
        InlineKeyboardButton(text="30 дней", callback_data="active_period:30"),
        InlineKeyboardButton(text="90 дней", callback_data="active_period:90"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_broadcast_target")
    )

    builder.adjust(3, 1)
    return builder.as_markup()


def get_regions_keyboard(regions: List[str], page: int = 1, items_per_page: int = 8):
    """Создает клавиатуру выбора региона с пагинацией."""
    builder = InlineKeyboardBuilder()

    total_pages = (len(regions) + items_per_page - 1) // items_per_page

    # Отображаем элементы текущей страницы
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(regions))

    current_page_regions = regions[start_idx:end_idx]

    for region in current_page_regions:
        builder.add(InlineKeyboardButton(
            text=region,
            callback_data=f"select_region:{region}"
        ))

    # Навигационные кнопки
    nav_buttons = []

    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"regions_page:{page - 1}"
        ))

    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="ignored"
        ))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"regions_page:{page + 1}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка назад
    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_broadcast_target"
    ))

    builder.adjust(1)
    return builder.as_markup()


def get_templates_keyboard(templates: List[tuple], page: int = 1, items_per_page: int = 5):
    """Создает клавиатуру выбора шаблона рассылки с пагинацией."""
    builder = InlineKeyboardBuilder()

    total_pages = (len(templates) + items_per_page - 1) // items_per_page

    # Отображаем элементы текущей страницы
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(templates))

    current_page_templates = templates[start_idx:end_idx]

    for template in current_page_templates:
        template_id, name, _, _, _, _ = template
        builder.add(InlineKeyboardButton(
            text=name,
            callback_data=f"select_template:{template_id}"
        ))

    # Навигационные кнопки
    nav_buttons = []

    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"templates_page:{page - 1}"
        ))

    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="ignored"
        ))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"templates_page:{page + 1}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка создания нового шаблона
    builder.row(InlineKeyboardButton(
        text="➕ Создать новый шаблон",
        callback_data="create_new_template"
    ))

    # Кнопка назад
    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_broadcast_menu"
    ))

    builder.adjust(1)
    return builder.as_markup()


def get_broadcast_preview_keyboard(with_buttons: bool = False, buttons_data: Optional[List] = None):
    """Создает клавиатуру для превью рассылки."""
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки из сообщения, если они есть
    if with_buttons and buttons_data:
        try:
            for button_row in buttons_data:
                row_buttons = []
                for button in button_row:
                    row_buttons.append(InlineKeyboardButton(
                        text=button["text"],
                        url=button.get("url", "https://example.com")  # Используем url для предпросмотра
                    ))
                if row_buttons:
                    builder.row(*row_buttons)
        except (KeyError, TypeError):
            # Если структура кнопок некорректная, игнорируем
            pass

    # Добавляем кнопки управления
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="✏️ Изменить текст", callback_data="edit_broadcast_text")
    )

    if with_buttons:
        builder.row(InlineKeyboardButton(
            text="🔘 Редактировать кнопки",
            callback_data="edit_broadcast_buttons"
        ))

    builder.row(InlineKeyboardButton(
        text="↩️ Отменить рассылку",
        callback_data="cancel_broadcast"
    ))

    builder.adjust(1)
    return builder.as_markup()


def get_broadcast_history_keyboard(broadcast_id: int):
    """Создает клавиатуру для просмотра деталей рассылки."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="📊 Статистика доставки",
            callback_data=f"broadcast_stats:{broadcast_id}"
        ),
        InlineKeyboardButton(
            text="↩️ Назад к истории",
            callback_data="broadcast_history"
        )
    )

    builder.adjust(1)
    return builder.as_markup()


def get_broadcast_history_list_keyboard(broadcasts: List[tuple], page: int = 1, items_per_page: int = 5):
    """Создает клавиатуру списка истории рассылок с пагинацией."""
    builder = InlineKeyboardBuilder()

    total_pages = (len(broadcasts) + items_per_page - 1) // items_per_page

    # Отображаем элементы текущей страницы
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(broadcasts))

    current_page_broadcasts = broadcasts[start_idx:end_idx]

    for broadcast in current_page_broadcasts:
        broadcast_id, _, _, _, _, status, created_at, _ = broadcast
        date_str = created_at.split(" ")[0] if isinstance(created_at, str) else "N/A"
        status_icon = "✅" if status == "completed" else "🕒" if status == "pending" else "❌"

        builder.add(InlineKeyboardButton(
            text=f"{status_icon} Рассылка #{broadcast_id} от {date_str}",
            callback_data=f"view_broadcast:{broadcast_id}"
        ))

    # Навигационные кнопки
    nav_buttons = []

    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"history_page:{page - 1}"
        ))

    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="ignored"
        ))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"history_page:{page + 1}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка назад
    builder.row(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_broadcast_menu"
    ))

    builder.adjust(1)
    return builder.as_markup()


def get_button_edit_keyboard():
    """Создает клавиатуру для редактирования кнопок."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="add_button"),
        InlineKeyboardButton(text="❌ Удалить кнопку", callback_data="remove_button"),
        InlineKeyboardButton(text="✅ Готово", callback_data="buttons_done"),
        InlineKeyboardButton(text="↩️ Отмена", callback_data="cancel_button_edit")
    )

    builder.adjust(1)
    return builder.as_markup()


def get_confirm_cancel_keyboard(confirm_data: str, cancel_data: str):
    """Создает клавиатуру с кнопками подтверждения и отмены."""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_data)
    )

    builder.adjust(2)
    return builder.as_markup()


def get_back_keyboard(callback_data="back_to_broadcast_menu"):
    """Создает простую клавиатуру с кнопкой "Назад"."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data=callback_data))
    return builder.as_markup()