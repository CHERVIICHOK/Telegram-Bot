from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData


class PromoCallback(CallbackData, prefix="promo"):
    action: str  # view, apply, etc.
    promo_id: int


def get_discounts_menu_keyboard() -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для главного меню раздела скидок."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Активные промокоды", callback_data="list_active_promos")
    builder.button(text="🔥 Текущие акции", callback_data="list_active_actions")
    builder.button(text="⌨️ Ввести промокод", callback_data="enter_promo_code")
    builder.button(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_active_promos_keyboard(promos: list) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком активных промокодов."""
    builder = InlineKeyboardBuilder()
    for promo in promos:
        # promo: (id, code, description, discount_type, discount_value, min_order_amount)
        promo_id, code, _, _, _, _ = promo
        builder.button(
            text=f"🎟️ {code}",
            callback_data=PromoCallback(action="view", promo_id=promo_id).pack()
        )
    builder.button(text="⬅️ Назад", callback_data="discounts_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_promo_details_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата из просмотра деталей промокода."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ К списку промокодов", callback_data="list_active_promos")
    return builder.as_markup()


def get_back_to_discounts_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата в меню скидок."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в меню скидок", callback_data="discounts_menu")
    return builder.as_markup()


def get_cart_keyboard(promo_applied: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if promo_applied:
        builder.button(text="❌ Убрать промокод", callback_data="remove_promo")
    else:
        # Эта кнопка ведет в меню скидок, чтобы пользователь мог выбрать/ввести промокод
        builder.button(text="🎁 Применить промокод", callback_data="discounts_menu")

    builder.button(text="✅ Оформить заказ", callback_data="checkout")
    builder.button(text="⬅️ В главное меню", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_go_to_cart_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Перейти в корзину", callback_data="cart")
    builder.button(text="⬅️ Назад в меню скидок", callback_data="discounts_menu")
    builder.adjust(1)
    return builder.as_markup()
