import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database.users.database import set_order_discount
from filters.admin_filter import AdminFilter
from states.admin_order_state import AdminOrderProcess
from keyboards.admins.order_process_keyboard import get_back_to_admin_panel_keyboard, get_confirm_order_keyboard
from keyboards.admins.menu_keyboard import get_admin_menu_keyboard
from database.users.warehouse_connection import get_product_id_by_full_name, update_product_quantity, \
    get_product_quantity

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание роутера
router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

@router.callback_query(F.data == "process_order")
async def start_process_order(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс обработки заказа"""
    await state.set_state(AdminOrderProcess.WAITING_ORDER_INFO)
    await callback.message.edit_text(
        "Пожалуйста, отправьте сообщение о заказе, состоящее из десяти пунктов:\n"
        "0. ID заказа"
        "1. Словарь вида: полное название товара :- количество...\n"
        "2. Дата доставки\n"
        "3. Время доставки\n"
        "4. Адрес доставки\n"
        "5. Имя пользователя\n"
        "6. Социальная сеть\n"
        "7. Телефон пользователя\n"
        "8. Имя продажника\n"
        "9. Стоимость без учета скидки\n"
        "10. Способ оплаты",
        reply_markup=get_back_to_admin_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_admin_panel", StateFilter(AdminOrderProcess))
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Возвращает админа к панели управления"""
    await state.clear()
    await callback.message.edit_text(
        "Панель управления администратора",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.message(StateFilter(AdminOrderProcess.WAITING_ORDER_INFO))
async def process_order_info(message: Message, state: FSMContext):
    """Обрабатывает информацию о заказе"""
    # Разделяем сообщение на строки и убираем пустые строки
    lines = [line.strip() for line in message.text.split('\n') if line.strip()]

    # Проверка количества пунктов
    if len(lines) != 11:
        await message.answer(
            f"Требуется ровно 11 пунктов информации. Обнаружено {len(lines)}. "
            "Пожалуйста, проверьте ввод и попробуйте снова.",
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        return

    # Проверка формата товаров (первый пункт) и создание словаря
    try:
        products_dict = {}
        order_id = lines[0]
        product_line = lines[1]

        if product_line.startswith("1."):
            product_line = product_line[2:].strip()

        # Разбиваем строку по запятым для получения отдельных товаров
        product_items = [item.strip() for item in product_line.split(',,')]

        if not product_items:
            raise ValueError("Не указаны товары")

        for item in product_items:
            parts = item.split(" :- ")
            if len(parts) != 2:
                raise ValueError(f"Неверный формат товара: '{item}'")

            product_name = parts[0].strip()
            try:
                quantity = int(parts[1].strip())
                if quantity <= 0:
                    raise ValueError(f"Количество товара '{product_name}' должно быть положительным числом")
            except ValueError:
                raise ValueError(f"Количество товара '{product_name}' должно быть целым числом")

            # Добавляем товар в словарь
            products_dict[product_name] = quantity

        # Проверяем, что словарь не пустой
        if not products_dict:
            raise ValueError("Не удалось распознать ни один товар")

    except ValueError as e:
        await message.answer(
            f"Некорректный формат данных о товарах: {str(e)}. "
            f"Требуется формат: 'Название товара - количество, Название товара - количество, ...'",
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        return

    # Проверка формата стоимости (девятый пункт)
    try:
        cost = lines[9]
        if cost.startswith("9."):
            cost = cost[2:].strip()

        cost = float(cost)
        if cost < 0:
            raise ValueError("Отрицательная стоимость")
    except ValueError:
        await message.answer(
            "Некорректный формат стоимости. Пожалуйста, укажите числовое значение.",
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        return

    delivery_date = lines[2]
    delivery_time = lines[3]
    delivery_address = lines[4]
    user_name = lines[5]
    social_network = lines[6]
    phone = lines[7]
    seller_name = lines[8]
    payment_method = lines[10]

    if order_id.startswith("0. "):
        order_id = order_id[2:].strip()

    if delivery_date.startswith("2."):
        delivery_date = delivery_date[2:].strip()

    if delivery_time.startswith("3."):
        delivery_time = delivery_time[2:].strip()

    if delivery_address.startswith("4."):
        delivery_address = delivery_address[2:].strip()

    if user_name.startswith("5."):
        user_name = user_name[2:].strip()

    if social_network.startswith("6."):
        social_network = social_network[2:].strip()

    if phone.startswith("7."):
        phone = phone[2:].strip()

    if seller_name.startswith("8."):
        seller_name = seller_name[2:].strip()

    if payment_method.startswith("10."):
        payment_method = payment_method[2:].strip()

    # Сохраняем данные заказа в состоянии
    await state.update_data(
        order_id=order_id,
        products=products_dict,
        delivery_date=delivery_date,
        delivery_time=delivery_time,
        delivery_address=delivery_address,
        user_name=user_name,
        social_network=social_network,
        phone=phone,
        seller_name=seller_name,
        cost=cost,
        payment_method=payment_method
    )

    # Переходим к вводу скидки
    await state.set_state(AdminOrderProcess.WAITING_DISCOUNT)
    await message.answer(
        "Пожалуйста, введите Вкус скидки (или 0, если скидки нет):",
        reply_markup=get_back_to_admin_panel_keyboard()
    )


@router.message(StateFilter(AdminOrderProcess.WAITING_DISCOUNT))
async def process_discount(message: Message, state: FSMContext):
    """Обрабатывает ввод скидки"""
    # Проверка формата скидки
    try:
        discount = float(message.text)
        if discount < 0:
            await message.answer(
                "Скидка не может быть отрицательной. Пожалуйста, введите положительное число или 0.",
                reply_markup=get_back_to_admin_panel_keyboard()
            )
            return
    except ValueError:
        await message.answer(
            "Пожалуйста, введите скидку в числовом формате (например: 100 или 100.50).",
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        return

    # Получаем данные заказа
    order_data = await state.get_data()
    cost = order_data.get("cost")

    # Проверка на превышение скидки стоимости
    if discount > cost:
        await message.answer(
            "Скидка превышает стоимость заказа.",
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        return

    # Рассчитываем стоимость с учетом скидки
    try:
        final_cost = cost - discount
    except Exception as e:
        logger.error(f"Ошибка при расчете стоимости: {e}")
        await message.answer(
            "Произошла ошибка при расчете стоимости. Пожалуйста, проверьте введенные данные.",
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        return

    # Обновляем данные заказа, добавляя скидку и финальную стоимость
    order_data["discount"] = discount
    order_data["final_cost"] = final_cost
    await state.update_data(order_data)

    # Формируем итоговый заказ для отображения
    products_str = ", ".join([f"{name}: {qty}" for name, qty in order_data["products"].items()])

    order_summary = (
        f"📋 <b>Информация о заказе:</b>\n\n"
        f"🛒 <b>Товары:</b> {products_str}\n"
        f"📅 <b>Дата доставки:</b> {order_data['delivery_date']}\n"
        f"🕒 <b>Время доставки:</b> {order_data['delivery_time']}\n"
        f"📍 <b>Адрес доставки:</b> {order_data['delivery_address']}\n"
        f"👤 <b>Имя пользователя:</b> {order_data['user_name']}\n"
        f"🌐 <b>Социальная сеть:</b> {order_data['social_network']}\n"
        f"📱 <b>Телефон:</b> {order_data['phone']}\n"
        f"👨‍💼 <b>Продажник:</b> {order_data['seller_name']}\n"
        f"💰 <b>Стоимость без скидки:</b> {order_data['cost']} руб.\n"
        f"🔻 <b>Скидка:</b> {discount} руб.\n"
        f"💵 <b>Итоговая стоимость:</b> {final_cost} руб.\n"
        f"💳 <b>Способ оплаты:</b> {order_data['payment_method']}"
    )

    # Переходим к подтверждению заказа
    await state.set_state(AdminOrderProcess.CONFIRM_ORDER)
    await message.answer(
        order_summary,
        reply_markup=get_confirm_order_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_order", StateFilter(AdminOrderProcess.CONFIRM_ORDER))
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждает заказ и обновляет количество товаров на складе"""
    order_data = await state.get_data()
    products = order_data.get("products", {})
    order_id = order_data.get("order_id")  # Получаем ID существующего заказа
    discount = order_data.get("discount", 0)  # Получаем скидку или используем 0 по умолчанию

    # Список для хранения результатов обработки товаров
    results = []
    success_count = 0

    # Обработка каждого товара
    for product_name, quantity in products.items():
        try:
            # Получаем ID товара
            product_id = get_product_id_by_full_name(product_name)

            if not product_id:
                results.append(f"❌ Товар '{product_name}' не найден в базе данных.")
                continue

            # Получаем текущее количество товара
            current_quantity = get_product_quantity(product_id)

            if current_quantity is None:
                results.append(f"❌ Не удалось получить текущее количество товара '{product_name}'.")
                continue

            # Проверяем, достаточно ли товара на складе
            if current_quantity < quantity:
                results.append(f"❌ Недостаточное количество товара '{product_name}' на складе. "
                               f"Требуется: {quantity}, доступно: {current_quantity}.")
                continue

            # Обновляем количество товара
            new_quantity = current_quantity - quantity
            if update_product_quantity(product_id, new_quantity):
                success_count += 1
                results.append(f"✅ Товар '{product_name}' обработан успешно. "
                               f"Новое количество: {new_quantity}.")
            else:
                results.append(f"❌ Произошла ошибка при обновлении количества товара '{product_name}'.")

        except Exception as e:
            logger.error(f"Ошибка при обработке товара {product_name}: {e}")
            results.append(f"❌ Произошла ошибка при обработке товара '{product_name}': {str(e)}")

    # Формируем отчет о результатах
    if success_count == len(products):
        status_message = "✅ Заказ успешно обработан! Количество товаров на складе обновлено."

        # Устанавливаем скидку для заказа
        if order_id:
            set_order_discount(order_id, discount)
            logger.info(f"Установлена скидка {discount} для заказа {order_id}")
        else:
            logger.error("Не удалось установить скидку: ID заказа не найден")

        # TODO: Здесь должна функция update_order_status(order_id, "Подтвержден")
    elif success_count == 0:
        status_message = "❌ Не удалось обработать заказ. Ни один товар не был обновлен в базе данных."
    else:
        status_message = f"⚠️ Частичное выполнение: успешно обработано {success_count} из {len(products)} товаров."

    # Формируем полный отчет
    full_report = status_message + "\n\n" + "\n".join(results)

    # Отправляем отчет и возвращаемся к панели управления
    await state.clear()
    try:
        await callback.message.edit_text(
            full_report,
            reply_markup=get_admin_menu_keyboard()
        )
    except TelegramBadRequest:
        # Если сообщение слишком длинное, отправляем новое
        await callback.message.answer(
            full_report,
            reply_markup=get_admin_menu_keyboard()
        )

    await callback.answer()
