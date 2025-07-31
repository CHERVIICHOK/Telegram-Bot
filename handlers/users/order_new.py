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
from states.order_state import OrderState
from keyboards.users.order_keyboards import (
    get_payment_method_kb,
    get_order_confirmation_kb, get_delivery_date_kb, get_delivery_time_kb,
    get_skip_comment_kb, get_cancel_kb, get_back_cancel_kb, get_edit_order_kb, get_skip_phone_number_kb
)
from database.users.database import (
    get_db_connection, save_order, save_order_item, get_cart_items,
    clear_cart, save_incomplete_order, get_incomplete_order, delete_incomplete_order, get_product_category
)

router = Router()

logger = logging.getLogger(__name__)


# Начало оформления заказа из корзины
@router.callback_query(F.data == "cart:checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    # Проверяем, не пуста ли корзина
    cart_items = get_cart_items(callback.from_user.id)

    if not cart_items:
        await callback.answer("Ваша корзина пуста!")
        return

    # Проверяем, есть ли незавершенный заказ
    conn = get_db_connection()
    incomplete_state, incomplete_data = get_incomplete_order(conn, callback.from_user.id)

    if incomplete_state and incomplete_data:
        builder = InlineKeyboardBuilder()
        builder.button(text="Продолжить оформление", callback_data="resume_order")
        builder.button(text="Начать заново", callback_data="restart_order")
        builder.button(text="❌ Отменить заказ", callback_data="cancel_order_process")
        builder.adjust(1)

        await callback.message.answer(
            "У вас есть незавершенный заказ. Хотите продолжить оформление?",
            reply_markup=builder.as_markup()
        )
        return

    # Сразу начинаем с ввода имени, минуя проверку возраста
    await state.set_state(OrderState.name)
    await callback.message.answer(
        "Пожалуйста, введите ваше имя:",
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

    # Проверяем, был ли это возврат после редактирования
    current_data = await state.get_data()
    if 'phone' in current_data and 'delivery_date' in current_data:
        # Это редактирование, возвращаемся к подтверждению
        await show_order_confirmation(message, state, message.from_user.id)
        return

    # Продолжаем обычный поток
    await state.set_state(OrderState.phone)

    await message.answer(
        "Введите ваш номер телефона в формате +7XXXXXXXXXX:",
        reply_markup=get_skip_phone_number_kb()
    )

    # await message.answer(
    #     "Введите ваш номер телефона в формате +7XXXXXXXXXX:",
    #     reply_markup=get_back_cancel_kb("name")
    # )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "name", await state.get_data())


# Обработка ввода телефона
@router.message(StateFilter(OrderState.phone))
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    # Простая валидация телефона через регулярное выражение
    phone_pattern = r'^\+?[0-9]{10,12}$'
    if not re.match(phone_pattern, phone):
        await message.answer(
            "Некорректный формат номера телефона. Пожалуйста, введите номер в формате +7XXXXXXXXXX или нажмите на кнопку 'Пропустить':",
            reply_markup=get_skip_phone_number_kb()
        )
        return

    # После сохранения телефона
    await state.update_data(phone=phone)

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'delivery_date' in current_data and 'delivery_time' in current_data:
        # Это редактирование
        await show_order_confirmation(message, state, message.from_user.id)
        return

    # Запрашиваем дату доставки
    await state.set_state(OrderState.delivery_date)
    await message.answer(
        "Выберите дату доставки или введите её вручную в формате ДД.ММ.ГГГГ (например, 23.03.2025):",
        reply_markup=get_delivery_date_kb()
    )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "phone", await state.get_data())


# Обработчик кнопки "Пропустить" при вводе номера телефона
@router.callback_query(lambda c: c.data == "skip_phone_number")
async def process_skip_phone(callback: CallbackQuery, state: FSMContext):
    # Устанавливаем пустое значение для телефона
    await state.update_data(phone="")

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'delivery_date' in current_data and 'delivery_time' in current_data:
        # Это редактирование
        await show_order_confirmation(callback.message, state, callback.from_user.id)
        return

    # Переходим к следующему шагу (дата доставки)
    await state.set_state(OrderState.delivery_date)

    # Отвечаем на callback
    await callback.answer()
    await callback.message.edit_text(
        "Выберите дату доставки или введите её вручную в формате ДД.ММ.ГГГГ (например, 23.03.2025):",
        reply_markup=get_delivery_date_kb()
    )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "phone", await state.get_data())


# Обработка ручного ввода даты доставки
@router.message(StateFilter(OrderState.delivery_date))
async def process_manual_date(message: Message, state: FSMContext):
    manual_date = message.text.strip()

    # Проверяем формат даты (ДД.ММ.ГГГГ)
    date_pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(202[4-9])$'
    if not re.match(date_pattern, manual_date):
        await message.answer(
            "Некорректный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 25.03.2024) или выберите из предложенных вариантов:",
            reply_markup=get_delivery_date_kb()
        )
        return

    # Проверяем, что дата не в прошлом
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

    # Сохраняем введенную дату
    await state.update_data(delivery_date=manual_date)

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'delivery_time' in current_data and 'delivery_type' in current_data:
        # Это редактирование
        await show_order_confirmation(message, state, message.from_user.id)
        return

    # Переходим к выбору времени доставки
    await state.set_state(OrderState.delivery_time)
    await message.answer(
        f"Выбрана дата: {manual_date}\n\nВыберите удобное время доставки или введите своё в формате ЧЧ:ММ (например, 14:30):",
        reply_markup=get_delivery_time_kb()
    )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "delivery_date", await state.get_data())


# Обработка выбора даты доставки
@router.callback_query(StateFilter(OrderState.delivery_date), F.data.startswith("date_"))
async def process_delivery_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("date_", "")

    # После сохранения даты
    await state.update_data(delivery_date=date_str)

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'delivery_time' in current_data and 'delivery_type' in current_data:
        # Это редактирование
        await show_order_confirmation(callback.message, state, callback.from_user.id)
        return

    # Переходим к выбору времени доставки
    await state.set_state(OrderState.delivery_time)
    await callback.message.answer(
        f"Выбрана дата: {date_str}\n\nВыберите удобное время доставки или введите своё в формате ЧЧ:ММ (например, 14:30):",
        reply_markup=get_delivery_time_kb()
    )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "delivery_date", await state.get_data())

    await callback.answer()


# Обработка ручного ввода времени доставки
@router.message(StateFilter(OrderState.delivery_time))
async def process_manual_time(message: Message, state: FSMContext):
    manual_time = message.text.strip()

    # Проверяем формат времени (можно использовать более строгую проверку)
    time_pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'
    if not re.match(time_pattern, manual_time):
        await message.answer(
            "Некорректный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30):",
            reply_markup=get_delivery_time_kb()
        )
        return

    # Сохраняем введенное время
    await state.update_data(delivery_time=manual_time)

    # Устанавливаем тип доставки "Курьером" по умолчанию
    await state.update_data(delivery_type="Курьером")

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'delivery_address' in current_data and 'payment_method' in current_data:
        # Это редактирование
        await show_order_confirmation(message, state, message.from_user.id)
        return

    # Переходим к вводу адреса доставки
    await state.set_state(OrderState.delivery_address)
    await message.answer(
        "Введите адрес доставки (улица, дом, квартира):",
        reply_markup=get_back_cancel_kb("delivery_time")
    )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "delivery_time", await state.get_data())


# Обработка выбора времени доставки
@router.callback_query(StateFilter(OrderState.delivery_time), F.data.startswith("time_"))
async def process_delivery_time(callback: CallbackQuery, state: FSMContext):
    time_slot = callback.data.replace("time_", "")
    # После сохранения времени
    await state.update_data(delivery_time=time_slot)

    # Устанавливаем тип доставки "Курьером" по умолчанию
    await state.update_data(delivery_type="Курьером")

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'delivery_address' in current_data and 'payment_method' in current_data:
        # Это редактирование
        await show_order_confirmation(callback.message, state, callback.from_user.id)
        return

    # Переходим сразу к вводу адреса доставки, минуя выбор типа доставки
    await state.set_state(OrderState.delivery_address)
    await callback.message.answer(
        "Введите адрес доставки (улица, дом, квартира):",
        reply_markup=get_back_cancel_kb("delivery_time")
    )

    # Сохраняем данные незавершенного заказа
    conn = get_db_connection()
    save_incomplete_order(conn, callback.from_user.id, "delivery_time", await state.get_data())

    await callback.answer()


# Обработка выбора типа доставки
@router.callback_query(StateFilter(OrderState.delivery_type))
async def process_delivery_type(callback: CallbackQuery, state: FSMContext):
    if callback.data == "delivery_type_pickup":
        delivery_type = "Самовывоз"
        # После сохранения типа доставки
        await state.update_data(delivery_type=delivery_type)

        # Проверка режима редактирования
        current_data = await state.get_data()
        if 'payment_method' in current_data:
            # Это редактирование
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return

        # Пропускаем ввод адреса и переходим к способу оплаты
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

    if len(address) < 5:
        await message.answer(
            "Адрес слишком короткий. Пожалуйста, введите полный адрес:",
            reply_markup=get_back_cancel_kb("delivery_type")
        )
        return

    # После сохранения адреса
    await state.update_data(delivery_address=address)

    # Проверка режима редактирования
    current_data = await state.get_data()
    if 'payment_method' in current_data:
        # Это редактирование
        await show_order_confirmation(message, state, message.from_user.id)
        return

    await state.set_state(OrderState.payment_method)

    await message.answer(
        "Выберите способ оплаты:",
        reply_markup=get_payment_method_kb()
    )

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "delivery_address", await state.get_data())


# Обработка выбора способа оплаты
@router.callback_query(StateFilter(OrderState.payment_method))
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    if callback.data == "payment_transfer":
        payment_method = "Перевод"
        # После сохранения способа оплаты
        await state.update_data(payment_method=payment_method)

        # Проверка режима редактирования
        current_data = await state.get_data()
        if 'comment' in current_data or current_data.get('comment') == '':
            # Это редактирование
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return
        await state.set_state(OrderState.comment)

        await callback.message.answer(
            "Добавьте комментарий к заказу или нажмите 'Пропустить':",
            reply_markup=get_skip_comment_kb()
        )
    elif callback.data == "payment_cash":
        payment_method = "Наличные при получении"
        # После сохранения способа оплаты
        await state.update_data(payment_method=payment_method)

        # Проверка режима редактирования
        current_data = await state.get_data()
        if 'comment' in current_data or current_data.get('comment') == '':
            # Это редактирование
            await show_order_confirmation(callback.message, state, callback.from_user.id)
            return
        await state.set_state(OrderState.comment)

        await callback.message.answer(
            "Добавьте комментарий к заказу или нажмите 'Пропустить':",
            reply_markup=get_skip_comment_kb()
        )
    elif callback.data == "go_back_payment":
        # Всегда возвращаемся к вводу адреса доставки, так как тип доставки всегда "Курьером"
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
    await show_order_confirmation(callback.message, state, user_id=callback.from_user.id)
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
    # После сохранения комментария
    await state.update_data(comment=comment)

    # Для комментария не нужна особая проверка, так как это последний шаг
    # Сразу вызываем show_order_confirmation

    conn = get_db_connection()
    save_incomplete_order(conn, message.from_user.id, "comment", await state.get_data())

    await show_order_confirmation(message, state, message.from_user.id)


# Показ подтверждения заказа
async def show_order_confirmation(message: Message, state: FSMContext, user_id=None):
    data = await state.get_data()

    user_id = user_id or message.from_user.id
    cart_items = get_cart_items(user_id)

    total_amount = 0

    for item in cart_items:
        total_amount += item['total_price']

    order_text = "📋 <b>Ваш заказ:</b>\n\n"

    order_text += "<b>Товары:</b>\n"
    for i, item in enumerate(cart_items, 1):
        order_text += f"{i}. {item['product_full_name']} x {item['quantity']} = {item['total_price']:.2f} ₽\n"

    order_text += f"\n<b>Итого:</b> {total_amount:.2f} ₽\n\n"
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
        # Сохраняем заказ в базу данных
        data = await state.get_data()
        conn = get_db_connection()

        # Создаем заказ
        order_id = save_order(
            conn,
            callback.from_user.id,
            data['name'],
            data['phone'],
            data['delivery_date'],
            data['delivery_time'],
            data['delivery_type'],
            data['delivery_address'],
            data['payment_method'],
            data.get('comment', '')
        )

        # Сохраняем элементы заказа
        cart_items = get_cart_items(callback.from_user.id)

        total_amount = 0
        for item in cart_items:
            total_amount += item['total_price']
            save_order_item(conn, order_id[0], item['product_id'], item['quantity'], item['price'])

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
                    all_cost_product.append(position['total_price'])
                    all_order_product_short_name.append(
                        position['product_full_name'].replace(position['flavor'], '', 1).strip())
                    all_order_flavors.append(position['flavor'])
                    all_order_category.append(get_product_category(position['product_full_name']))
            all_cost_product.append(position['total_price'])
            all_order_product_short_name.append(position['product_full_name'].replace(position['flavor'], '', 1).strip())
            all_order_flavors.append(position['flavor'])
            all_order_category.append(get_product_category(position['product_full_name']))

        positions = []
        for position in range(len(all_order_product_short_name)):
            admin_order_text = f"""
0. {all_order_category[position]}
1. {all_order_product_short_name[position]}
2. {all_order_flavors[position]}
3. {data['delivery_date']}
4. {data['delivery_time']}
5. {data['delivery_address']}
6. {data['name']}
7. Telegram, @{callback.from_user.username}
8. {data['phone']}
9. Bot
10. {all_cost_product[position]:.2f}
11. 0
12. {data['payment_method']}
            """
            positions.append(admin_order_text)

        for i, item in enumerate(cart_items, 1):
            header_admin_note += f"{item['product_full_name']} : {item['quantity']},\n"
            header_admin_note += f"{i}. {item['product_full_name']} x {item['quantity']} = {item['total_price']:.2f} ₽\n"

        header_admin_note = header_admin_note.rstrip(", ")

        if data.get('comment'):
            header_admin_note += f"Комментарий: {data['comment']}"

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
                            str(message)
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

        # Удаляем незавершенный заказ
        delete_incomplete_order(conn, callback.from_user.id)

        # Уведомляем клиента
        await callback.message.answer(
            "✅ Ваш заказ успешно оформлен!\n\n"
            f"Номер заказа: #{order_id[1]}\n\n"
            "В ближайшее время с вами свяжется наш менеджер для подтверждения заказа."
        )

        # try:
        #     from utils.stock_notification_utils import check_low_stock_products
        #     wh_conn = create_connection_warehouse()
        #     shop_conn = get_db_connection()
        #     await check_low_stock_products(wh_conn, shop_conn, callback.bot)
        #     wh_conn.close()
        #     shop_conn.close()
        # except Exception as e:
        #     logger.error(f"Ошибка при проверке товаров с низким остатком: {e}")

        await state.clear()

    elif callback.data == "edit_order":
        # Вместо возврата к началу предлагаем выбрать, что редактировать
        data = await state.get_data()
        await state.set_state(OrderState.edit_selection)

        await callback.message.answer(
            "Выберите, какую информацию вы хотели бы изменить:",
            reply_markup=get_edit_order_kb(data.get('delivery_type', ''))
        )

    elif callback.data == "cancel_order":
        # Удаляем незавершенный заказ
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
        # Возвращаемся к вводу имени
        await state.set_state(OrderState.name)
        await callback.message.answer(
            "Пожалуйста, введите ваше имя:",
            reply_markup=get_cancel_kb()
        )

    elif prev_state == "delivery_date":
        # Возвращаемся к вводу телефона
        await state.set_state(OrderState.phone)
        await callback.message.answer(
            "Введите ваш номер телефона в формате +7XXXXXXXXXX:",
            reply_markup=get_skip_phone_number_kb()
        )


    elif prev_state == "delivery_time":
        # Возвращаемся к выбору даты доставки
        await state.set_state(OrderState.delivery_date)
        await callback.message.answer(
            "Выберите дату доставки:",
            reply_markup=get_delivery_date_kb()
        )

    elif prev_state == "delivery_type":
        # Возвращаемся к выбору времени доставки
        await state.set_state(OrderState.delivery_time)
        data = await state.get_data()
        await callback.message.answer(
            f"Выбрана дата: {data.get('delivery_date', 'не указана')}\n\nТеперь выберите удобное время доставки:",
            reply_markup=get_delivery_time_kb()
        )


    elif prev_state == "payment":
        # Возвращаемся к адресу доставки (так как тип доставки всегда "Курьером")
        await state.set_state(OrderState.delivery_address)
        await callback.message.answer(
            "Введите адрес доставки (улица, дом, квартира):",
            reply_markup=get_back_cancel_kb("delivery_time")
        )

    await callback.answer()


# Обработчик для отмены заказа
@router.callback_query(F.data == "cancel_order_process")
async def handle_cancel_order(callback: CallbackQuery, state: FSMContext):
    # Удаляем незавершенный заказ
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

    # Восстанавливаем данные состояния
    await state.set_data(incomplete_data)

    # Определяем, с какого состояния продолжить
    if incomplete_state == "name":
        await state.set_state(OrderState.name)
        await callback.message.answer(
            "Пожалуйста, введите ваше имя:",
            reply_markup=get_cancel_kb()
        )
    elif incomplete_state == "phone":
        await state.set_state(OrderState.phone)
        await callback.message.answer(
            "Введите ваш номер телефона в формате +7XXXXXXXXXX:",
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
            f"Выбрана дата: {incomplete_data['delivery_date']}\n\nВыберите удобное время доставки или введите своё в формате ЧЧ:ММ (например, 14:30):",
            reply_markup=get_delivery_time_kb()
        )
    elif incomplete_state == "delivery_type":
        # Устанавливаем тип доставки "Курьером"
        await state.update_data(delivery_type="Курьером")

        # Переходим сразу к вводу адреса
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
            "Добавьте комментарий к заказу или нажмите 'Пропустить':",
            reply_markup=get_skip_comment_kb()
        )
    else:
        # Если не можем определить состояние, начинаем заново
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
            reply_markup=get_skip_phone_number_kb()  # Используем клавиатуру с кнопкой "Пропустить"
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
            f"Текущий комментарий: {data.get('comment', 'не указан')}\nВведите новый комментарий или нажмите 'Пропустить':",
            reply_markup=get_skip_comment_kb()
        )

    elif callback.data == "back_to_confirmation":
        # Возвращаемся к подтверждению заказа
        await show_order_confirmation(callback.message, state, callback.from_user.id)

    elif callback.data == "cancel_order":
        # Удаляем незавершенный заказ
        conn = get_db_connection()
        delete_incomplete_order(conn, callback.from_user.id)
        await callback.message.answer("Заказ отменен.")
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "restart_order")
async def restart_order(callback: CallbackQuery, state: FSMContext):
    # Удаляем незавершенный заказ
    conn = get_db_connection()
    delete_incomplete_order(conn, callback.from_user.id)

    # Начинаем оформление заново
    await start_checkout(callback, state)
