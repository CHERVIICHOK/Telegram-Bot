from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_back_to_admin_panel_keyboard():
    """Создает клавиатуру с кнопкой возврата к панели управления"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="⬅️ Вернуться к панели управления",
        callback_data="back_to_admin_panel"
    ))
    return builder.as_markup()


def get_confirm_order_keyboard():
    """Создает клавиатуру с кнопками подтверждения заказа и возврата к панели управления"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order"),
        InlineKeyboardButton(text="⬅️ Вернуться к панели управления", callback_data="back_to_admin_panel")
    )
    builder.adjust(1)
    return builder.as_markup()
