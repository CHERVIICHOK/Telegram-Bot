from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.users.discounts_keyboards import (
    get_discounts_menu_keyboard,
    get_active_promos_keyboard,
    get_promo_details_keyboard,
    get_back_to_discounts_menu_keyboard,
    PromoCallback, get_go_to_cart_keyboard
)
from states.discounts_states import DiscountStates
from database.discounts_db import DiscountsDatabase

discounts_router = Router()
db = DiscountsDatabase()  # В реальном проекте лучше передавать экземпляр через middleware


# --- Helper Function ---
def format_promo_details(promo_data: dict) -> str:
    """Форматирует детали промокода для вывода пользователю."""
    discount_str = f"{int(promo_data['discount_value'])}%" if promo_data[
                                                                  'discount_type'] == 'percentage' else f"{int(promo_data['discount_value'])} ₽"

    details = [
        f"🏷️ <b>Промокод:</b> <code>{promo_data['code']}</code>",
        f"📄 <b>Описание:</b> {promo_data['description']}",
        f"💸 <b>Скидка:</b> {discount_str}",
    ]
    if promo_data['min_order_amount'] > 0:
        details.append(f"💰 <b>Мин. сумма заказа:</b> {int(promo_data['min_order_amount'])} ₽")

    details.append(f"📅 <b>Действует до:</b> {promo_data['end_date']}")

    return "\n".join(details)


# --- Handlers ---

async def send_discounts_menu(message_or_callback):
    text = "Добро пожаловать в раздел акций и скидок! 🎉\n\nВыберите интересующий вас раздел:"
    keyboard = get_discounts_menu_keyboard()

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)


@discounts_router.callback_query(F.data == "discounts_menu")
async def show_discounts_menu_callback(callback: CallbackQuery):
    await send_discounts_menu(callback)


@discounts_router.message(F.text == "🎁 Акции и скидки")
async def show_discounts_menu_message(message: Message):
    await send_discounts_menu(message)


# Показать список активных промокодов
@discounts_router.callback_query(F.data == "list_active_promos")
async def list_active_promos(callback: CallbackQuery):
    active_promos = db.get_active_promo_codes()
    if not active_promos:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет активных промокодов.",
            reply_markup=get_back_to_discounts_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            "Вот список доступных промокодов. Нажмите на любой, чтобы узнать подробности:",
            reply_markup=get_active_promos_keyboard(active_promos)
        )
    await callback.answer()


# Показать детали конкретного промокода
@discounts_router.callback_query(PromoCallback.filter("view" == F.action))
async def show_promo_details(callback: CallbackQuery, callback_data: PromoCallback):
    promo_id = callback_data.promo_id
    promo_details_raw = db.get_promo_code_details(promo_id)

    if not promo_details_raw:
        await callback.answer("Промокод не найден!", show_alert=True)
        return

    # Преобразуем кортеж в словарь для удобства
    promo_dict = {
        'id': promo_details_raw[0], 'code': promo_details_raw[1], 'description': promo_details_raw[2],
        'discount_type': promo_details_raw[3], 'discount_value': promo_details_raw[4],
        'min_order_amount': promo_details_raw[5], 'start_date': promo_details_raw[6],
        'end_date': promo_details_raw[7]
    }

    text = format_promo_details(promo_dict)

    # Логируем просмотр
    db.log_promo_view(promo_id=promo_id, user_id=callback.from_user.id)

    await callback.message.edit_text(text, reply_markup=get_promo_details_keyboard())
    await callback.answer()


# Показать "Товар дня"
@discounts_router.callback_query(F.data == "show_daily_deal")
async def show_daily_deal(callback: CallbackQuery):
    deal = db.get_daily_deal()
    if not deal:
        await callback.message.edit_text(
            "😔 На сегодня специальных предложений нет. Загляните завтра!",
            reply_markup=get_back_to_discounts_menu_keyboard()
        )
    else:
        # deal: (product_id, description, discount_type, discount_value)
        _, description, discount_type, discount_value = deal
        discount_str = f"{int(discount_value)}%" if discount_type == 'percentage' else f"{int(discount_value)} ₽"
        text = (
            f"🔥 <b>Товар дня!</b> 🔥\n\n"
            f"{description}\n"
            f"<b>Скидка:</b> {discount_str}\n\n"
            f"<i>*Скидка применится автоматически при добавлении товара в корзину.</i>"
        )
        await callback.message.edit_text(text, reply_markup=get_back_to_discounts_menu_keyboard())
    await callback.answer()


# Начать процесс ввода промокода
@discounts_router.callback_query(F.data == "enter_promo_code")
async def enter_promo_code_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Пожалуйста, отправьте мне текст вашего промокода.")
    await state.set_state(DiscountStates.waiting_for_promo_code)
    await callback.answer()


# Обработать введенный промокод
@discounts_router.message(DiscountStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    user_code = message.text.strip().upper()
    promo_data, status_message = db.validate_promo_code(user_code)

    # Очищаем состояние в любом случае
    await state.clear()

    if promo_data:
        # Сохраняем только код в состояние. Этого достаточно.
        await state.update_data(applied_promo_code=promo_data['code'])

        final_message = (
            f"✅ {status_message}\n\n"
            f"{format_promo_details(promo_data)}\n\n"
            "Скидка будет применена в вашей корзине. Вы можете перейти в нее сейчас."
        )
        # НОВОЕ: предлагаем сразу перейти в корзину
        await message.answer(final_message, reply_markup=get_go_to_cart_keyboard())
    else:
        await message.answer(
            f"❌ Ошибка: {status_message}",
            reply_markup=get_back_to_discounts_menu_keyboard()
        )


@discounts_router.callback_query(F.data == "list_active_actions")
async def list_active_actions(callback: CallbackQuery):
    active_actions = db.get_active_actions()

    if not active_actions:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет активных акций. Загляните позже!",
            reply_markup=get_back_to_discounts_menu_keyboard()
        )
        await callback.answer()
        return

    response_text = "<b>🔥 Наши текущие акции:</b>\n\n"

    for action in active_actions:
        title, desc, d_type, d_val, end_date = action
        discount_str = f"{int(d_val)}%" if d_type == 'percentage' else f"{int(d_val)} ₽"

        response_text += (
            f"<b>{title}</b>\n"
            f"<i>{desc}</i>\n"
            f"<b>Выгода:</b> {discount_str}\n"
            f"<b>Действует до:</b> {end_date}\n"
            "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        )

    await callback.message.edit_text(response_text, reply_markup=get_back_to_discounts_menu_keyboard())
    await callback.answer()
