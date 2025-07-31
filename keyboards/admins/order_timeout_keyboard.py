from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_timeout_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает главное меню настроек таймаута"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⏱️ Время первого уведомления",
            callback_data="timeout_first_notification"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Интервал повторных уведомлений",
            callback_data="timeout_interval"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Текст уведомления",
            callback_data="timeout_text"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data="admin_menu"
        )
    )

    return builder.as_markup()


def get_timeout_settings_keyboard(current_timeout: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для настройки времени первого уведомления"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=f"⏱️ Текущее время: {current_timeout} мин.",
            callback_data="ignore"
        )
    )
    builder.adjust(3)

    builder.row(
        InlineKeyboardButton(
            text=f"10 мин.",
            callback_data=f"set_timeout:{10}"
        )
    )
    quick_times = [15, 20, 30, 60]
    for time in quick_times:
        builder.add(
            InlineKeyboardButton(
                text=f"{time} мин.",
                callback_data=f"set_timeout:{time}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="⌨️ Ввести другое время",
            callback_data="custom_timeout"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="timeout_settings"
        )
    )

    return builder.as_markup()


def get_interval_settings_keyboard(current_interval: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для настройки интервала повторных уведомлений"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=f"🔄 Текущий интервал: {current_interval} мин.",
            callback_data="ignore"
        )
    )
    builder.adjust(3)

    builder.row(
        InlineKeyboardButton(
            text=f"{5} мин.",
            callback_data=f"set_interval:{5}"
        )
    )

    quick_intervals = [10, 15, 30, 60]
    for interval in quick_intervals:
        builder.add(
            InlineKeyboardButton(
                text=f"{interval} мин.",
                callback_data=f"set_interval:{interval}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="⌨️ Ввести другой интервал",
            callback_data="custom_interval"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="timeout_settings"
        )
    )

    return builder.as_markup()


def get_text_settings_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для настройки текста уведомления"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить текст",
            callback_data="edit_notification_text"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Сбросить на стандартный",
            callback_data="reset_notification_text"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="timeout_settings"
        )
    )

    return builder.as_markup()


def get_confirm_timeout_keyboard(minutes: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения изменения таймаута"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm_timeout:{minutes}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="timeout_first_notification"
        )
    )

    return builder.as_markup()


def get_confirm_interval_keyboard(minutes: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения изменения интервала"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm_interval:{minutes}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="timeout_interval"
        )
    )

    return builder.as_markup()


def get_confirm_text_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения изменения текста"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Сохранить",
            callback_data="confirm_notification_text"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="timeout_text"
        )
    )

    return builder.as_markup()
