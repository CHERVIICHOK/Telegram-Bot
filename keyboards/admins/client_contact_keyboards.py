from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_message_type_keyboard():
    """Клавиатура для выбора типа сообщения"""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="📝 Текстовое сообщение", callback_data="msg_type_text"),
        InlineKeyboardButton(text="🖼️ Изображение с текстом", callback_data="msg_type_image")
    )
    builder.add(
        InlineKeyboardButton(text="Отмена", callback_data="client_contact_cancel")
    )
    builder.adjust(1)

    return builder.as_markup()


def get_confirm_keyboard(user_id: int):
    """Клавиатура подтверждения отправки"""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="✅ Отправить",
            callback_data=f"confirm_send_{user_id}"
        ),
        InlineKeyboardButton(
            text="✏️ Изменить сообщение",
            callback_data="edit_message"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="Отмена",
            callback_data="client_contact_cancel"
        )
    )
    builder.adjust(2, 1)

    return builder.as_markup()


def get_back_to_menu_keyboard():
    """Клавиатура для возврата в главное меню"""
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="📋 Главное меню",
            callback_data="admin_menu"
        ),
        InlineKeyboardButton(
            text="💬 Отправить ещё",
            callback_data="client_contact"
        )
    )
    builder.adjust(1)

    return builder.as_markup()


def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены (ReplyKeyboard)"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_inline_cancel_keyboard():
    """Inline клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Отмена", callback_data="client_contact_cancel"))
    return builder.as_markup()