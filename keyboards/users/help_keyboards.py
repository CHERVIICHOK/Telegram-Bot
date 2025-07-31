from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_help_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq"),
        InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="help_contact"),
        InlineKeyboardButton(text="🚚 Информация о доставке", callback_data="help_delivery"),
        InlineKeyboardButton(text="💳 Способы оплаты", callback_data="help_payment"),
        # InlineKeyboardButton(text="↩️ Политика возврата", callback_data="help_refund"),
        InlineKeyboardButton(text="⭐ Оценить бота", callback_data="help_feedback"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_help_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔙 Назад к разделу помощи", callback_data="back_to_help"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_contact_support_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📱 Написать менеджеру", url="https://t.me/zaxhz"),
        InlineKeyboardButton(text="🔙 Назад к разделу помощи", callback_data="back_to_help"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    builder.adjust(1)
    return builder.as_markup()


def get_rating_keyboard():
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text="⭐", callback_data="rating_1"),
        InlineKeyboardButton(text="⭐️⭐", callback_data="rating_2"),
        InlineKeyboardButton(text="⭐️⭐⭐", callback_data="rating_3"),
        InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating_4"),
        InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating_5"),
    )

    builder.add(
        InlineKeyboardButton(text="🔙 Назад к разделу помощи", callback_data="back_to_help"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )

    builder.adjust(3, 2, 2)

    return builder.as_markup()