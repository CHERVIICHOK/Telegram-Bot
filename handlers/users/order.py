import datetime
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.admins.orders_bd import update_order_status
from database.admins.staff_db import get_staff_by_role
from database.discounts_db import DiscountsDatabase
from states.order_state import OrderState
from keyboards.users.order_keyboards import (
    get_payment_method_kb,
    get_order_confirmation_kb, get_delivery_date_kb, get_delivery_time_kb,
    get_skip_comment_kb, get_cancel_kb, get_back_cancel_kb, get_edit_order_kb, get_skip_phone_number_kb,
    get_delivery_address_kb, get_promo_code_kb
)
from database.users.database import (
    get_db_connection, save_order_item, get_cart_items,
    clear_cart, save_incomplete_order, get_incomplete_order, delete_incomplete_order, get_product_category,
    get_user_past_addresses, calculate_cart_total, save_order_with_promo
)
from utils.order_timeout_manager import order_timeout_manager

router = Router()

logger = logging.getLogger(__name__)

discounts_db = DiscountsDatabase()


def calculate_discount(promo_data, cart_total, cart_items):
    """
    Рассчитывает размер скидки на основе промокода и корзины
    """
    if not promo_data:
        return 0.0, "Промокод не применен"

    # Проверяем минимальную сумму заказа
    if cart_total < promo_data['min_order_amount']:
        return 0.0, f"Минимальная сумма заказа для этого промокода: {promo_data['min_order_amount']:.2f} ₽"

    # Рассчитываем скидку
    if promo_data['discount_type'] == 'percentage':
        discount = cart_total * (promo_data['discount_value'] / 100)
        # Ограничиваем процентную скидку разумными пределами (например, максимум 50% от суммы)
        max_discount = cart_total * 0.5
        discount = min(discount, max_discount)
    else:  # fixed_amount
        discount = promo_data['discount_value']

    # Скидка не может быть больше суммы заказа
    discount = min(discount, cart_total)

    return discount, "Скидка успешно применена!"


def calculate_action_discount(cart_items):
    """
    Рассчитывает скидку от активных акций
    Возвращает: (общая_скидка, детали_акций, примененные_акции)
    """
    applicable_actions = discounts_db.get_active_actions_for_products(cart_items)

    if not applicable_actions:
        return 0.0, [], []

    total_action_discount = 0.0
    action_details = []
    applied_actions = []

    # Группируем товары по акциям для избежания двойного применения
    processed_items = set()

    for action in applicable_actions:
        action_discount = 0.0
        affected_items = []

        for item in action['applicable_items']:
            item_key = f"{item['product_id']}_{item['product_full_name']}"

            # Проверяем, не был ли товар уже обработан другой акцией
            if item_key not in processed_items:
                item_total = item['total_price']

                if action['discount_type'] == 'percentage':
                    item_discount = item_total * (action['discount_value'] / 100)
                else:  # fixed_amount
                    # Для фиксированной скидки применяем к каждой единице товара
                    item_discount = min(action['discount_value'] * item['quantity'], item_total)

                action_discount += item_discount
                affected_items.append({
                    'product_name': item['product_full_name'],
                    'quantity': item['quantity'],
                    'original_price': item_total,
                    'discount': item_discount
                })
                processed_items.add(item_key)

        if action_discount > 0:
            total_action_discount += action_discount
            action_details.append({
                'title': action['title'],
                'description': action['description'],
                'discount_amount': action_discount,
                'affected_items': affected_items
            })
            applied_actions.append(action)

    return total_action_discount, action_details, applied_actions


def compare_discounts(promo_discount, promo_data, action_discount, action_details):
    """
    Сравнивает скидки от промокода и акций, возвращает наиболее выгодный вариант
    Возвращает: (тип_скидки, размер_скидки, детали)
    """
    if promo_discount > action_discount:
        return 'promo', promo_discount, {
            'promo_code': promo_data['code'] if promo_data else '',
            'promo_data': promo_data
        }
    elif action_discount > 0:
        return 'action', action_discount, {
            'action_details': action_details
        }
    else:
        return 'none', 0.0, {}


def format_discount_info(discount_type, discount_amount, discount_details):
    """Форматирует информацию о примененной скидке для отображения пользователю"""
    if discount_type == 'none' or discount_amount <= 0:
        return ""

    info = f"💰 Применена скидка: {discount_amount:.2f} ₽\n"

    if discount_type == 'promo':
        promo_code = discount_details.get('promo_code', '')
        info += f"📋 Промокод: {promo_code}\n"
    elif discount_type == 'action':
        info += "🎉 Активные акции:\n"
        for action in discount_details.get('action_details', []):
            info += f"• {action['title']}: -{action['discount_amount']:.2f} ₽\n"

    return info


def check_available_discounts(user_id):
    """
    Проверяет доступные скидки для пользователя
    Возвращает информацию о доступных акциях
    """
    cart_total, cart_items = calculate_cart_total(user_id)
    action_discount, action_details, applied_actions = calculate_action_discount(cart_items)

    if action_discount > 0:
        return {
            'has_discounts': True,
            'discount_amount': action_discount,
            'action_details': action_details,
            'message': f"🎉 Для товаров в вашей корзине доступны акции! Экономия: {action_discount:.2f} ₽"
        }

    return {
        'has_discounts': False,
        'discount_amount': 0.0,
        'action_details': [],
        'message': ""
    }


# Начало оформления заказа из корзины
@router.callback_query(F.data == "cart:checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    cart_items = get_cart_items(callback.from_user.id)

    if not cart_items:
        await callback.answer("Ваша корзина пуста!")
        return

    # Проверяем доступные акции
    discount_info = check_available_discounts(callback.from_user.id)

    conn = get_db_connection()
    incomplete_state, incomplete_data = get_incomplete_order(conn, callback.from_user.id)

    if incomplete_state and incomplete_data:
        builder = InlineKeyboardBuilder()
        builder.button(text="Продолжить оформление", callback_data="resume_order")
        builder.button(text="Начать заново", callback_data="restart_order")
        builder.button(text="❌ Отменить заказ", callback_data="cancel_order_process")
        builder.adjust(1)

        message_text = "У вас есть незавершенный заказ. Хотите продолжить оформление?"
        if discount_info['has_discounts']:
            message_text += f"\n\n{discount_info['message']}"

        await callback.message.answer(
            message_text,
            reply_markup=builder.as_markup()
        )
        return

    await state.set_state(OrderState.name)

    message_text = "Пожалуйста, введите ваше имя:"
    if discount_info['has_discounts']:
        message_text = f"{discount_info['message']}\n\n{message_text}"

    await callback.message.answer(
        message_text,
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


# Обработка ввода имени
@router.message(StateFilter(OrderState.name))
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "Имя должно содержать минимум 2 символа. Пожалуйста, введите корректное имя:",
            reply_markup=get_cancel_kb()
        )
        return

    await state.update_data(name=name)

    current_data = await state.get_data()
    if 'phone' in current_data and 'delivery_date' in current_data:
        await show_order_confirmation(message, state, message.from_user.id)
        return

    # Продолжаем обычный поток
    await state.set_state(OrderState.phone)

    await message.answer(
        "Введите ваш номер телефона в формате +7...",
        reply_markup=get_skip_phone_number_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "name", await state.get_data())


# Обработка ввода телефона
@router.message(StateFilter(OrderState.phone))
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    phone_pattern = r'^\+?[0-9]{10,12}$'
    if not re.match(phone_pattern, phone):
        await message.answer(
            "Некорректный формат номера телефона. Пожалуйста, введите номер в формате +7... или нажмите на кнопку 'Пропустить':",
            reply_markup=get_skip_phone_number_kb()
        )
        return

    await state.update_data(phone=phone)

    current_data = await state.get_data()
    if 'delivery_date' in current_data and 'delivery_time' in current_data:
        await show_order_confirmation(message, state, message.from_user.id)
        return

    await state.set_state(OrderState.delivery_date)
    await message.answer(
        "Выберите дату доставки или введите её вручную в формате ДД.ММ.ГГГГ (например, 23.03.2025):",
        reply_markup=get_delivery_date_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "phone", await state.get_data())


# Обработчик кнопки "Пропустить" при вводе номера телефона
@router.callback_query(lambda c: c.data == "skip_phone_number")
async def process_skip_phone(callback: CallbackQuery, state: FSMContext):
    await state.update_data(phone="")

    current_data = await state.get_data()
    if 'delivery_date' in current_data and 'delivery_time' in current_data:
        await show_order_confirmation(callback.message, state, callback.from_user.id)
        return

    await state.set_state(OrderState.delivery_date)

    await callback.answer()
    await callback.message.edit_text(
        "Выберите дату доставки или введите её вручную в формате ДД.ММ.ГГГГ (например, 23.03.2025):",
        reply_markup=get_delivery_date_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "phone", await state.get_data())


# Обработка ручного ввода даты доставки
@router.message(StateFilter(OrderState.delivery_date))
async def process_manual_date(message: Message, state: FSMContext):
    manual_date = message.text.strip()

    date_pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(202[4-9])$'
    if not re.match(date_pattern, manual_date):
        await message.answer(
            "Некорректный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 25.03.2024) или "
            "выберите из предложенных вариантов:",
            reply_markup=get_delivery_date_kb()
        )
        return

    try:
        day, month, year = map(int, manual_date.split('.'))
        input_date = datetime.date(year, month, day)
        today = datetime.date.today()

        if input_date < today:
            await message.answer(
                "Выбранная дата находится в прошлом. Пожалуйста, выберите дату начиная с сегодняшнего дня:",
                reply_markup=get_delivery_date_kb()
            )
            return
    except ValueError:
        await message.answer(
            "Введена некорректная дата. Пожалуйста, проверьте правильность даты и введите в формате ДД.ММ.ГГГГ:",
            reply_markup=get_delivery_date_kb()
        )
        return

    await state.update_data(delivery_date=manual_date)

    current_data = await state.get_data()
    if 'delivery_time' in current_data and 'delivery_type' in current_data:
        await show_order_confirmation(message, state, message.from_user.id)
        return

    await state.set_state(OrderState.delivery_time)
    await message.answer(
        f"Выбрана дата: {manual_date}\n\nВыберите удобное время доставки или введите своё в формате ЧЧ:ММ (например, 16:20):",
        reply_markup=get_delivery_time_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "delivery_date", await state.get_data())


# Обработка выбора даты доставки
@router.callback_query(StateFilter(OrderState.delivery_date), F.data.startswith("date_"))
async def process_delivery_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("date_", "")

    await state.update_data(delivery_date=date_str)

    current_data = await state.get_data()
    if 'delivery_time' in current_data and 'delivery_type' in current_data:
        await show_order_confirmation(callback.message, state, callback.from_user.id)
        return

    await state.set_state(OrderState.delivery_time)
    await callback.message.answer(
        f"Выбрана дата: {date_str}\n\nВыберите удобное время доставки или введите своё в формате ЧЧ:ММ (например, 16:20):",
        reply_markup=get_delivery_time_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "delivery_date", await state.get_data())

    await callback.answer()


# Обработка ручного ввода времени доставки
@router.message(StateFilter(OrderState.delivery_time))
async def process_manual_time(message: Message, state: FSMContext):
    manual_time = message.text.strip()

    time_pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'
    if not re.match(time_pattern, manual_time):
        await message.answer(
            "Некорректный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 16:20):",
            reply_markup=get_delivery_time_kb()
        )
        return

    await state.update_data(delivery_time=manual_time)

    await state.update_data(delivery_type="Курьером")

    current_data = await state.get_data()
    if 'delivery_address' in current_data and 'payment_method' in current_data:
        await show_order_confirmation(message, state, message.from_user.id)
        return

    await state.set_state(OrderState.delivery_address)
    await message.answer(
        "Введите адрес доставки (улица, дом, квартира):",
        reply_markup=get_back_cancel_kb("delivery_time")
    )

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "delivery_time", await state.get_data())


# Обработка выбора времени доставки
@router.callback_query(StateFilter(OrderState.delivery_time), F.data.startswith("time_"))
async def process_delivery_time(callback: CallbackQuery, state: FSMContext):
    time_slot = callback.data.replace("time_", "")
    await state.update_data(delivery_time=time_slot)
    await state.update_data(delivery_type="Курьером")

    current_data = await state.get_data()
    if 'delivery_address' in current_data and 'payment_method' in current_data:
        await show_order_confirmation(callback.message, state, callback.from_user.id)
        return

    await state.set_state(OrderState.delivery_address)

    past_addresses = get_user_past_addresses(callback.from_user.id)

    if past_addresses:
        await state.update_data(past_addresses=past_addresses)

        await callback.message.edit_text(
            "Выберите адрес доставки из списка или введите новый:",
            reply_markup=get_delivery_address_kb(callback.from_user.id)
        )
    else:
        await callback.message.edit_text(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )

    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "delivery_time", await state.get_data())

    await callback.answer()


# Обработка выбора типа доставки
@router.callback_query(StateFilter(OrderState.delivery_type))
async def process_delivery_type(callback: CallbackQuery, state: FSMContext):
    if callback.data == "delivery_type_pickup":
        delivery_type = "Самовывоз"
        await state.update_data(delivery_type=delivery_type)

        current_data = await state.get_data()
        if 'payment_method' in current_data:
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return

        await state.set_state(OrderState.payment_method)
        await callback.message.answer(
            "Выберите способ оплаты:",
            reply_markup=get_payment_method_kb()
        )
    elif callback.data == "delivery_type_courier":
        delivery_type = "Курьером"
        await state.update_data(delivery_type=delivery_type)

        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_type")
        )
    elif callback.data == "go_back_delivery_time":
        await handle_go_back(callback, state)
    elif callback.data == "cancel_order_process":
        await handle_cancel_order(callback, state)

    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "delivery_type", await state.get_data())

    await callback.answer()


# Обработка ввода адреса доставки
@router.message(StateFilter(OrderState.delivery_address))
async def process_delivery_address(message: Message, state: FSMContext):
    address = message.text.strip()

    if len(address) < 3:
        await message.answer(
            "Адрес слишком короткий. Пожалуйста, введите полный адрес:",
            reply_markup=get_back_cancel_kb("delivery_type")
        )
        return

    await state.update_data(delivery_address=address)

    current_data = await state.get_data()
    if 'payment_method' in current_data:
        await show_order_confirmation(message, state, message.from_user.id)
        return

    await state.set_state(OrderState.payment_method)

    await message.answer(
        "Выберите способ оплаты:",
        reply_markup=get_payment_method_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "delivery_address", await state.get_data())


# Обработка выбора адреса из истории
@router.callback_query(StateFilter(OrderState.delivery_address), F.data.startswith("past_address_"))
async def process_past_address_selection(callback: CallbackQuery, state: FSMContext):
    address_index = int(callback.data.replace("past_address_", ""))

    past_addresses = get_user_past_addresses(callback.from_user.id)

    if address_index < len(past_addresses):
        selected_address = past_addresses[address_index]

        await state.update_data(delivery_address=selected_address)

        current_data = await state.get_data()
        if 'payment_method' in current_data:
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return

        await state.set_state(OrderState.payment_method)
        await callback.message.edit_text(
            f"Адрес доставки: {selected_address}\n\nВыберите способ оплаты:",
            reply_markup=get_payment_method_kb()
        )

        conn = get_db_connection()
        save_incomplete_order(conn, callback.from_user.id, "delivery_address", await state.get_data())

    await callback.answer()


# Обработка кнопки "Ввести новый адрес"
@router.callback_query(StateFilter(OrderState.delivery_address), F.data == "new_address")
async def process_new_address_button(callback: CallbackQuery):
    await callback.message.edit_text(
        "Введите адрес доставки (улица, дом, квартира):",
        reply_markup=get_back_cancel_kb("delivery_type")
    )
    await callback.answer()


# Обработка игнорирования заголовка
@router.callback_query(F.data == "header_ignore")
async def ignore_header_click(callback: CallbackQuery):
    await callback.answer()


# Обработка выбора способа оплаты
@router.callback_query(StateFilter(OrderState.payment_method))
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    if callback.data == "payment_transfer":
        payment_method = "Перевод"
        await state.update_data(payment_method=payment_method)

        current_data = await state.get_data()
        if 'comment' in current_data or current_data.get('comment') == '':
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return
        await state.set_state(OrderState.comment)

        await callback.message.answer(
            "Добавьте комментарий к заказу или пропустите шаг:",
            reply_markup=get_skip_comment_kb()
        )
    elif callback.data == "payment_cash":
        payment_method = "Наличные при получении"
        await state.update_data(payment_method=payment_method)

        current_data = await state.get_data()
        if 'comment' in current_data or current_data.get('comment') == '':
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return
        await state.set_state(OrderState.comment)

        await callback.message.answer(
            "Добавьте комментарий к заказу или пропустите шаг:",
            reply_markup=get_skip_comment_kb()
        )
    elif callback.data == "go_back_payment":
        await state.set_state(OrderState.delivery_address)
        data = await state.get_data()
        await callback.message.answer(
            f"Текущий адрес: {data.get('delivery_address', 'не указан')}\nВведите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )
    elif callback.data == "cancel_order_process":
        await handle_cancel_order(callback, state)

    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "payment_method", await state.get_data())

    await callback.answer()


async def handle_go_back_to_delivery_address(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.delivery_address)
    await callback.message.answer(
        "Введите адрес доставки (улица, дом, квартира):",
        reply_markup=get_back_cancel_kb("delivery_type")
    )


# Обработка комментария или его пропуск
@router.callback_query(StateFilter(OrderState.comment), F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await state.update_data(comment="")

    # Переходим к вводу промокода вместо подтверждения
    await state.set_state(OrderState.promo_code)
    await callback.message.answer(
        "Введите промокод для получения скидки или пропустите этот шаг:",
        reply_markup=get_promo_code_kb()
    )
    await callback.answer()


@router.callback_query(StateFilter(OrderState.comment), F.data.startswith("go_back_"))
async def go_back_from_comment(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.payment_method)
    await callback.message.answer(
        "Выберите способ оплаты:",
        reply_markup=get_payment_method_kb()
    )
    await callback.answer()


@router.callback_query(StateFilter(OrderState.comment), F.data == "cancel_order_process")
async def cancel_from_comment(callback: CallbackQuery, state: FSMContext):
    await handle_cancel_order(callback, state)
    await callback.answer()


@router.message(StateFilter(OrderState.comment))
async def process_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    await state.update_data(comment=comment)

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "comment", await state.get_data())

    # Переходим к вводу промокода
    await state.set_state(OrderState.promo_code)
    await message.answer(
        "Введите промокод для получения скидки или пропустите этот шаг:",
        reply_markup=get_promo_code_kb()
    )


# Новые обработчики для промокодов
@router.callback_query(StateFilter(OrderState.promo_code), F.data == "skip_promo_code")
async def skip_promo_code(callback: CallbackQuery, state: FSMContext):
    # Проверяем доступные акции даже если промокод пропущен
    cart_total, cart_items = calculate_cart_total(callback.from_user.id)
    action_discount, action_details, applied_actions = calculate_action_discount(cart_items)

    if action_discount > 0:
        await state.update_data(
            promo_code="",
            discount_amount=action_discount,
            promo_data=None,
            discount_type='action',
            action_details=action_details
        )

        await callback.message.answer(
            f"💡 Для вас доступны акции!\n"
            f"💰 Размер скидки: {action_discount:.2f} ₽\n"
            f"💳 К оплате: {cart_total - action_discount:.2f} ₽"
        )
    else:
        await state.update_data(promo_code="", discount_amount=0.0, promo_data=None, discount_type='none')

    await show_order_confirmation(callback.message, state, user_id=callback.from_user.id)
    await callback.answer()


@router.message(StateFilter(OrderState.promo_code))
async def process_promo_code(message: Message, state: FSMContext):
    promo_code = message.text.strip().upper()

    # Получаем данные корзины
    cart_total, cart_items = calculate_cart_total(message.from_user.id)

    # Рассчитываем скидку от акций
    action_discount, action_details, applied_actions = calculate_action_discount(cart_items)

    # Валидируем промокод с учетом пользователя
    promo_data, validation_message = discounts_db.validate_promo_code_for_user(promo_code, message.from_user.id)

    if promo_data:
        # Рассчитываем скидку от промокода
        promo_discount, promo_message = calculate_discount(promo_data, cart_total, cart_items)

        if promo_discount > 0:
            # Сравниваем промокод и акции
            best_discount_type, best_discount_amount, best_discount_details = compare_discounts(
                promo_discount, promo_data, action_discount, action_details
            )

            if best_discount_type == 'promo':
                await state.update_data(
                    promo_code=promo_code,
                    discount_amount=best_discount_amount,
                    promo_data=promo_data,
                    discount_type='promo',
                    action_details=None
                )

                response_text = f"✅ {validation_message}\n"
                response_text += f"💰 Размер скидки: {best_discount_amount:.2f} ₽\n"

                if action_discount > 0:
                    response_text += f"\n💡 Промокод выгоднее акций (экономия: {best_discount_amount - action_discount:.2f} ₽)\n"

                response_text += f"💳 К оплате: {cart_total - best_discount_amount:.2f} ₽"

            else:  # Акции выгоднее
                await state.update_data(
                    promo_code="",
                    discount_amount=best_discount_amount,
                    promo_data=None,
                    discount_type='action',
                    action_details=action_details
                )

                response_text = f"💡 Акции выгоднее промокода!\n"
                response_text += f"💰 Размер скидки от акций: {best_discount_amount:.2f} ₽\n"
                response_text += f"📋 Промокод дал бы скидку: {promo_discount:.2f} ₽\n"
                response_text += f"💳 К оплате: {cart_total - best_discount_amount:.2f} ₽"

            await message.answer(response_text)

            conn = get_db_connection()
            save_incomplete_order(conn, message.from_user.id, "promo_code", await state.get_data())

            # Переходим к подтверждению заказа
            await show_order_confirmation(message, state, message.from_user.id)
        else:
            # Промокод не применился, проверяем акции
            if action_discount > 0:
                await state.update_data(
                    promo_code="",
                    discount_amount=action_discount,
                    promo_data=None,
                    discount_type='action',
                    action_details=action_details
                )

                response_text = f"❌ {promo_message}\n\n"
                response_text += f"💡 Но для вас доступны акции!\n"
                response_text += f"💰 Размер скидки от акций: {action_discount:.2f} ₽\n"
                response_text += f"💳 К оплате: {cart_total - action_discount:.2f} ₽"

                await message.answer(response_text)
                await show_order_confirmation(message, state, message.from_user.id)
            else:
                # Ни промокод, ни акции не применились
                await state.update_data(promo_code="", discount_amount=0.0, promo_data=None, discount_type='none')
                await message.answer(
                    f"❌ {promo_message}\n\n"
                    "Попробуйте ввести другой промокод или пропустите этот шаг:",
                    reply_markup=get_promo_code_kb()
                )
    else:
        # Промокод не прошел валидацию, проверяем акции
        if action_discount > 0:
            await state.update_data(
                promo_code="",
                discount_amount=action_discount,
                promo_data=None,
                discount_type='action',
                action_details=action_details
            )

            response_text = f"❌ {validation_message}\n\n"
            response_text += f"💡 Но для вас доступны акции!\n"
            response_text += f"💰 Размер скидки от акций: {action_discount:.2f} ₽\n"
            response_text += f"💳 К оплате: {cart_total - action_discount:.2f} ₽"

            await message.answer(response_text)
            await show_order_confirmation(message, state, message.from_user.id)
        else:
            # Ни промокод, ни акции не доступны
            await state.update_data(promo_code="", discount_amount=0.0, promo_data=None, discount_type='none')
            await message.answer(
                f"❌ {validation_message}\n\n"
                "Попробуйте ввести другой промокод или пропустите этот шаг:",
                reply_markup=get_promo_code_kb()
            )


@router.callback_query(StateFilter(OrderState.promo_code), F.data.startswith("go_back_"))
async def go_back_from_promo_code(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.comment)
    await callback.message.answer(
        "Добавьте комментарий к заказу или пропустите шаг:",
        reply_markup=get_skip_comment_kb()
    )
    await callback.answer()


@router.callback_query(StateFilter(OrderState.promo_code), F.data == "cancel_order_process")
async def cancel_from_promo_code(callback: CallbackQuery, state: FSMContext):
    await handle_cancel_order(callback, state)
    await callback.answer()


# Показ подтверждения заказа
async def show_order_confirmation(message: Message, state: FSMContext, user_id=None):
    data = await state.get_data()

    user_id = user_id or message.from_user.id
    cart_items = get_cart_items(user_id)

    total_amount = sum(item['total_price'] for item in cart_items)
    discount_amount = data.get('discount_amount', 0.0)
    discount_type = data.get('discount_type', 'none')
    final_amount = total_amount - discount_amount

    order_text = "📋 <b>Ваш заказ:</b>\n\n"

    order_text += "<b>Товары:</b>\n"
    for i, item in enumerate(cart_items, 1):
        order_text += f"{i}. {item['product_full_name']} x {item['quantity']} = {item['total_price']:.2f} ₽\n"

    order_text += f"\n<b>Сумма товаров:</b> {total_amount:.2f} ₽\n"

    # Показываем информацию о скидке в зависимости от типа
    if discount_amount > 0:
        if discount_type == 'promo':
            promo_code = data.get('promo_code', '')
            order_text += f"<b>Промокод:</b> {promo_code}\n"
            order_text += f"<b>Скидка:</b> -{discount_amount:.2f} ₽\n"
        elif discount_type == 'action':
            order_text += f"<b>Акции:</b>\n"
            action_details = data.get('action_details', [])
            for action in action_details:
                order_text += f"• {action['title']}: -{action['discount_amount']:.2f} ₽\n"
            order_text += f"<b>Общая скидка:</b> -{discount_amount:.2f} ₽\n"

        order_text += f"<b>К оплате:</b> {final_amount:.2f} ₽\n\n"
    else:
        order_text += f"<b>Итого:</b> {total_amount:.2f} ₽\n\n"

    order_text += "<b>Информация о заказе:</b>\n"
    order_text += f"Имя: {data['name']}\n"
    order_text += f"Телефон: {data['phone']}\n"
    order_text += f"Дата доставки: {data['delivery_date']}\n"
    order_text += f"Время доставки: {data['delivery_time']}\n"
    order_text += f"Способ доставки: {data['delivery_type']}\n"
    order_text += f"Адрес: {data['delivery_address']}\n"
    order_text += f"Способ оплаты: {data['payment_method']}\n"

    if data.get('comment'):
        order_text += f"Комментарий: {data['comment']}\n"

    order_text += "\nПожалуйста, проверьте данные заказа и подтвердите."

    await state.set_state(OrderState.confirmation)
    await message.answer(
        order_text,
        reply_markup=get_order_confirmation_kb(),
        parse_mode="HTML"
    )


# Обработка подтверждения заказа
@router.callback_query(StateFilter(OrderState.confirmation))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "confirm_order":
        data = await state.get_data()
        conn = get_db_connection()

        # Получаем данные о скидке
        discount_amount = data.get('discount_amount', 0.0)
        promo_data = data.get('promo_data')

        # Сохраняем заказ с учетом скидки
        order_id = save_order_with_promo(
            conn,
            callback.from_user.id,
            data['name'],
            data['phone'],
            data['delivery_date'],
            data['delivery_time'],
            data['delivery_type'],
            data['delivery_address'],
            data['payment_method'],
            data.get('comment', ''),
            data.get('promo_code', ''),
            discount_amount
        )

        cart_items = get_cart_items(callback.from_user.id)

        total_amount = sum(item['total_price'] for item in cart_items)
        final_amount = total_amount - discount_amount

        # Сохраняем товары заказа
        for item in cart_items:
            save_order_item(conn, order_id[0], item['product_id'], item['quantity'], item['price'])

            # Логируем использование промокода или акций
            discount_type = data.get('discount_type', 'none')

            if discount_type == 'promo' and promo_data and discount_amount > 0:
                try:
                    # Увеличиваем счетчик использований промокода
                    with discounts_db.connection:
                        discounts_db.cursor.execute(
                            "UPDATE promo_codes SET current_uses = current_uses + 1 WHERE id = ?",
                            (promo_data['id'],)
                        )

                    # Логируем использование
                    with discounts_db.connection:
                        discounts_db.cursor.execute("""
                                INSERT INTO promo_code_usage (promo_code_id, user_id, order_id, discount_amount, order_total)
                                VALUES (?, ?, ?, ?, ?)
                            """, (promo_data['id'], callback.from_user.id, order_id[0], discount_amount, total_amount))

                    logger.info(f"Промокод {data.get('promo_code')} успешно применен к заказу {order_id[0]}")
                except Exception as e:
                    logger.error(f"Ошибка при логировании использования промокода: {e}")

            elif discount_type == 'action' and discount_amount > 0:
                try:
                    # Логируем применение акций (можно расширить для детальной аналитики)
                    action_details = data.get('action_details', [])
                    for action in action_details:
                        logger.info(
                            f"Акция '{action['title']}' применена к заказу {order_id[0]}, скидка: {action['discount_amount']:.2f} ₽")
                except Exception as e:
                    logger.error(f"Ошибка при логировании применения акций: {e}")

        # Формируем сообщение для администраторов
        header_admin_note = f"🔔 <b>Новый заказ #{order_id[0]}</b>\n\n"
        header_admin_note += "<b>Товары:</b>\n"

        all_order_product_short_name = []
        all_order_flavors = []
        all_order_category = []
        all_cost_product = []

        for position in cart_items:
            quantity = position['quantity']
            if quantity > 1:
                for product in range(quantity - 1):
                    all_cost_product.append(position['price'])
                    all_order_product_short_name.append(
                        position['product_full_name'].replace(position['flavor'], '', 1).strip())
                    all_order_flavors.append(position['flavor'])
                    all_order_category.append(get_product_category(position['product_full_name']))
            all_cost_product.append(position['price'])
            all_order_product_short_name.append(
                position['product_full_name'].replace(position['flavor'], '', 1).strip())
            all_order_flavors.append(position['flavor'])
            all_order_category.append(get_product_category(position['product_full_name']))

        positions = []
        for position in range(len(all_order_product_short_name)):
            admin_order_text = (
                f"0. {all_order_category[position]}\n"
                f"1. {all_order_product_short_name[position]}\n"
                f"2. {all_order_flavors[position]}\n"
                f"3. {data['delivery_date']}\n"
                f"4. {data['delivery_time']}\n"
                f"5. {data['delivery_address']}\n"
                f"6. {data['name']}\n"
                f"7. Telegram, @{callback.from_user.username}\n"
                f"8. {data['phone']}\n"
                f"9. Bot\n"
                f"10. {all_cost_product[position]:.2f}\n"
                f"11. {discount_amount}\n"
                f"12. {data['payment_method']}\n"
                f"13. <code>{callback.from_user.id}</code>"
            )
            positions.append(admin_order_text)

        for i, item in enumerate(cart_items, 1):
            header_admin_note += f"{item['product_full_name']} : {item['quantity']},\n"
            header_admin_note += f"{i}. {item['product_full_name']} x {item['quantity']} = {item['total_price']:.2f} ₽\n"

        header_admin_note = header_admin_note.rstrip(", ")

        # Добавляем информацию о скидке в сообщение администратору
        if discount_amount > 0:
            header_admin_note += f"\n\n💰 <b>Применена скидка:</b>\n"

            if discount_type == 'promo':
                promo_code = data.get('promo_code', '')
                header_admin_note += f"Тип: Промокод ({promo_code})\n"
            elif discount_type == 'action':
                header_admin_note += f"Тип: Акции\n"
                action_details = data.get('action_details', [])
                for action in action_details:
                    header_admin_note += f"• {action['title']}: -{action['discount_amount']:.2f} ₽\n"

            header_admin_note += f"Размер скидки: {discount_amount:.2f} ₽\n"
            header_admin_note += f"Сумма без скидки: {total_amount:.2f} ₽\n"
            header_admin_note += f"К оплате: {final_amount:.2f} ₽"

        if data.get('comment'):
            header_admin_note += f"\n\nКомментарий: {data['comment']}"

        # Проверка на подозрительный заказ (учитываем финальную сумму)
        if final_amount > 3000:
            header_admin_note += (
                f"\n\n⚠️ <b>Внимание! Обнаружен подозрительный заказ!</b> Перед оформлением тщательно перепроверьте "
                f"информацию о клиенте. Если возникли сомнения, <b>свяжитесь с администратором.</b>"
            )

        try:
            # Отправка сообщений всем администраторам
            admins = get_staff_by_role(role="Админ")
            admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
            for admin_id in admin_ids:
                try:
                    await callback.bot.send_message(
                        admin_id,
                        header_admin_note,
                        parse_mode="HTML"
                    )
                    for message in positions:
                        await callback.bot.send_message(
                            admin_id,
                            str(message),
                            parse_mode="HTML"
                        )
                    logger.info(f"Заказ успешно отправлен администратору {admin_id}")
                except Exception as e:
                    logger.error(f"Не удалось отправить заказ администратору {admin_id}: {e}")

            # Отправка сообщений всем курьерам
            couriers = get_staff_by_role(role="Курьер")
            courier_ids = [courier['telegram_id'] for courier in couriers if courier.get('is_active', 1)]
            for courier_id in courier_ids:
                try:
                    await callback.bot.send_message(
                        courier_id,
                        header_admin_note,
                        parse_mode="HTML"
                    )
                    for message in positions:
                        await callback.bot.send_message(
                            courier_id,
                            str(message)
                        )
                    logger.info(f"Заказ успешно отправлен курьеру {courier_id}")
                except Exception as e:
                    logger.error(f"Не удалось отправить заказ курьеру {courier_id}: {e}")
        except Exception as e:
            logger.error(f"Общая ошибка при отправке заказа: {e}")

        clear_cart(callback.from_user.id)
        update_order_status(order_id, 'processing')
        await order_timeout_manager.start_timer(order_id[0], callback.bot)

        delete_incomplete_order(conn, callback.from_user.id)

        # Уведомляем клиента с учетом скидки
        client_message = "✅ Ваш заказ успешно оформлен!\n\n"
        client_message += f"Номер заказа: #{order_id[1]}\n"

        if discount_amount > 0:
            if discount_type == 'promo':
                client_message += f"💰 Применен промокод: {data.get('promo_code', '')}\n"
                client_message += f"💰 Размер скидки: {discount_amount:.2f} ₽\n"
            elif discount_type == 'action':
                client_message += f"🎉 Применены акции\n"
                client_message += f"💰 Размер скидки: {discount_amount:.2f} ₽\n"

            client_message += f"💳 К оплате: {final_amount:.2f} ₽\n"
        else:
            client_message += f"💳 Сумма к оплате: {total_amount:.2f} ₽\n"

        client_message += "\nВ ближайшее время с вами свяжется наш менеджер для подтверждения заказа."

        await callback.message.answer(client_message)
        await state.clear()

    elif callback.data == "edit_order":
        data = await state.get_data()
        await state.set_state(OrderState.edit_selection)

        await callback.message.answer(
            "Выберите, какую информацию вы хотели бы изменить:",
            reply_markup=get_edit_order_kb(data.get('delivery_type', ''))
        )

    elif callback.data == "cancel_order":
        conn = get_db_connection()
        delete_incomplete_order(conn, callback.from_user.id)

        await callback.message.answer("Заказ отменен.")
        await state.clear()

    await callback.answer()


# Обработчик для кнопки "Назад"
@router.callback_query(F.data.startswith("go_back_"))
async def handle_go_back(callback: CallbackQuery, state: FSMContext):
    prev_state = callback.data.replace("go_back_", "")

    if prev_state == "name":
        await callback.message.answer(
            "Вы вернулись к началу оформления заказа.",
        )
        await start_checkout(callback, state)
        return

    elif prev_state == "phone":
        await state.set_state(OrderState.name)
        await callback.message.answer(
            "Пожалуйста, введите ваше имя:",
            reply_markup=get_cancel_kb()
        )

    elif prev_state == "delivery_date":
        await state.set_state(OrderState.phone)
        await callback.message.answer(
            "Введите ваш номер телефона в формате +7...",
            reply_markup=get_skip_phone_number_kb()
        )


    elif prev_state == "delivery_time":
        await state.set_state(OrderState.delivery_date)
        await callback.message.answer(
            "Выберите дату доставки:",
            reply_markup=get_delivery_date_kb()
        )

    elif prev_state == "delivery_type":
        await state.set_state(OrderState.delivery_time)
        data = await state.get_data()
        await callback.message.answer(
            f"Выбрана дата: {data.get('delivery_date', 'не указана')}\n\nТеперь выберите удобное время доставки:",
            reply_markup=get_delivery_time_kb()
        )


    elif prev_state == "payment":
        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )

    await callback.answer()


# Обработчик для отмены заказа
@router.callback_query(F.data == "cancel_order_process")
async def handle_cancel_order(callback: CallbackQuery, state: FSMContext):
    conn = get_db_connection()
    delete_incomplete_order(conn, callback.from_user.id)

    await callback.message.answer("Оформление заказа отменено.")
    await state.clear()
    await callback.answer()


# Обработка возобновления незавершенного заказа
@router.callback_query(F.data == "resume_order")
async def resume_incomplete_order(callback: CallbackQuery, state: FSMContext):
    conn = get_db_connection()
    incomplete_state, incomplete_data = get_incomplete_order(conn, callback.from_user.id)

    if not incomplete_state or not incomplete_data:
        await callback.message.answer("Незавершенный заказ не найден. Начнем оформление заново.")
        await start_checkout(callback, state)
        return

    await state.set_data(incomplete_data)

    if incomplete_state == "name":
        await state.set_state(OrderState.name)
        await callback.message.answer(
            "Пожалуйста, введите ваше имя:",
            reply_markup=get_cancel_kb()
        )
    elif incomplete_state == "phone":
        await state.set_state(OrderState.phone)
        await callback.message.answer(
            "Введите ваш номер телефона в формате +7...",
            reply_markup=get_skip_phone_number_kb()
        )
    elif incomplete_state == "delivery_date":
        await state.set_state(OrderState.delivery_date)
        await callback.message.answer(
            "Выберите дату доставки:",
            reply_markup=get_delivery_date_kb()
        )
    elif incomplete_state == "delivery_time":
        await state.set_state(OrderState.delivery_time)
        await callback.message.answer(
            f"Выбрана дата: {incomplete_data['delivery_date']}\n\nВыберите удобное время доставки или введите "
            f"своё в формате ЧЧ:ММ (например, 16:20):",
            reply_markup=get_delivery_time_kb()
        )
    elif incomplete_state == "delivery_type":
        await state.update_data(delivery_type="Курьером")

        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )
    elif incomplete_state == "delivery_address":
        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )
    elif incomplete_state == "payment_method":
        await state.set_state(OrderState.payment_method)
        await callback.message.answer(
            "Выберите способ оплаты:",
            reply_markup=get_payment_method_kb()
        )
    elif incomplete_state == "comment":
        await state.set_state(OrderState.comment)
        await callback.message.answer(
            "Добавьте комментарий к заказу или пропустите шаг:",
            reply_markup=get_skip_comment_kb()
        )
    else:
        await callback.message.answer("Не удалось восстановить заказ. Начнем оформление заново.")
        await start_checkout(callback, state)

    await callback.answer()


# Обработка выбора параметра для редактирования
@router.callback_query(StateFilter(OrderState.edit_selection))
async def process_edit_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "edit_name":
        await state.set_state(OrderState.name)
        await callback.message.answer(
            f"Текущее имя: {data.get('name', '')}\nВведите новое имя:",
            reply_markup=get_cancel_kb()
        )

    elif callback.data == "edit_phone":
        await state.set_state(OrderState.phone)
        await callback.message.answer(
            f"Текущий телефон: {data.get('phone', '')}\nВведите новый номер телефона:",
            reply_markup=get_skip_phone_number_kb()
        )

    elif callback.data == "edit_delivery_date":
        await state.set_state(OrderState.delivery_date)
        await callback.message.answer(
            f"Текущая дата доставки: {data.get('delivery_date', '')}\nВыберите новую дату доставки:",
            reply_markup=get_delivery_date_kb()
        )

    elif callback.data == "edit_delivery_time":
        await state.set_state(OrderState.delivery_time)
        await callback.message.answer(
            f"Текущее время доставки: {data.get('delivery_time', '')}\nВыберите новое время доставки или введите своё в формате ЧЧ:ММ:",
            reply_markup=get_delivery_time_kb()
        )

    elif callback.data == "edit_address":
        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            f"Текущий адрес: {data.get('delivery_address', '')}\nВведите новый адрес доставки:",
            reply_markup=get_back_cancel_kb("edit_selection")
        )

    elif callback.data == "edit_payment":
        await state.set_state(OrderState.payment_method)
        await callback.message.answer(
            f"Текущий способ оплаты: {data.get('payment_method', '')}\nВыберите новый способ оплаты:",
            reply_markup=get_payment_method_kb()
        )

    elif callback.data == "edit_comment":
        await state.set_state(OrderState.comment)
        await callback.message.answer(
            f"Текущий комментарий: {data.get('comment', 'не указан')}\nВведите новый комментарий или пропустите шаг:",
            reply_markup=get_skip_comment_kb()
        )

    elif callback.data == "edit_promo_code":
        await state.set_state(OrderState.promo_code)
        current_promo = data.get('promo_code', 'не указан')
        current_discount = data.get('discount_amount', 0.0)
        promo_text = f"Текущий промокод: {current_promo}\n"
        if current_discount > 0:
            promo_text += f"Текущая скидка: {current_discount:.2f} ₽\n\n"
        promo_text += "Введите новый промокод или пропустите шаг для удаления текущего:"
        await callback.message.answer(
            promo_text,
            reply_markup=get_promo_code_kb()
        )

    elif callback.data == "back_to_confirmation":
        await show_order_confirmation(callback.message, state, callback.from_user.id)

    elif callback.data == "cancel_order":
        conn = get_db_connection()
        delete_incomplete_order(conn, callback.from_user.id)
        await callback.message.answer("Заказ отменен.")
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "resume_order")
async def resume_incomplete_order(callback: CallbackQuery, state: FSMContext):
    conn = get_db_connection()
    incomplete_state, incomplete_data = get_incomplete_order(conn, callback.from_user.id)

    if not incomplete_state or not incomplete_data:
        await callback.message.answer("Незавершенный заказ не найден. Начнем оформление заново.")
        await start_checkout(callback, state)
        return

    await state.set_data(incomplete_data)

    if incomplete_state == "name":
        await state.set_state(OrderState.name)
        await callback.message.answer(
            "Пожалуйста, введите ваше имя:",
            reply_markup=get_cancel_kb()
        )
    elif incomplete_state == "phone":
        await state.set_state(OrderState.phone)
        await callback.message.answer(
            "Введите ваш номер телефона в формате +7...",
            reply_markup=get_skip_phone_number_kb()
        )
    elif incomplete_state == "delivery_date":
        await state.set_state(OrderState.delivery_date)
        await callback.message.answer(
            "Выберите дату доставки:",
            reply_markup=get_delivery_date_kb()
        )
    elif incomplete_state == "delivery_time":
        await state.set_state(OrderState.delivery_time)
        await callback.message.answer(
            f"Выбрана дата: {incomplete_data['delivery_date']}\n\nВыберите удобное время доставки или введите "
            f"своё в формате ЧЧ:ММ (например, 16:20):",
            reply_markup=get_delivery_time_kb()
        )
    elif incomplete_state == "delivery_type":
        await state.update_data(delivery_type="Курьером")

        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )
    elif incomplete_state == "delivery_address":
        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )
    elif incomplete_state == "payment_method":
        await state.set_state(OrderState.payment_method)
        await callback.message.answer(
            "Выберите способ оплаты:",
            reply_markup=get_payment_method_kb()
        )
    elif incomplete_state == "comment":
        await state.set_state(OrderState.comment)
        await callback.message.answer(
            "Добавьте комментарий к заказу или пропустите шаг:",
            reply_markup=get_skip_comment_kb()
        )
    elif incomplete_state == "promo_code":
        await state.set_state(OrderState.promo_code)
        await callback.message.answer(
            "Введите промокод для получения скидки или пропустите этот шаг:",
            reply_markup=get_promo_code_kb()
        )
    else:
        await callback.message.answer("Не удалось восстановить заказ. Начнем оформление заново.")
        await start_checkout(callback, state)
