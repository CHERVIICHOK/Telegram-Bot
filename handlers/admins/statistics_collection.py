import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from database.users.warehouse_connection import get_total_value_db
from filters.admin_filter import AdminFilter
from keyboards.admins.statistics_collection_keyboards import (
    get_statistics_menu_keyboard,
    get_back_to_statistics_keyboard,
    get_pagination_keyboard
)
from keyboards.admins.menu_keyboard import get_admin_menu_keyboard
from database.admins.statistics_db import (
    get_total_sales_statistics,
    get_delivered_orders,
    get_profit_statistics
)
from states.statistics_collection_state import StatisticsState

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

logger = logging.getLogger(__name__)


# Обработчик для отображения меню статистики
@router.callback_query(F.data == "admin_statistics")
async def show_statistics_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик для перехода в меню статистики"""
    await state.clear()
    await callback.message.edit_text(
        "📈 Меню статистики\n\n"
        "Выберите тип статистики для просмотра:",
        reply_markup=get_statistics_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "calculate_warehouse_value")
async def calculate_warehouse_value(callback: CallbackQuery):
    try:
        total_value = get_total_value_db()

        # Форматирование числа с разделителями тысяч
        formatted_value = f"{total_value:,.2f}".replace(',', ' ')

        await callback.message.edit_text(
            f"💰 Общая стоимость товаров на складе: {formatted_value} ₽\n\n"
            f"Расчет выполнен на основе текущих остатков товаров и их закупочных цен.",
            reply_markup=get_back_to_statistics_keyboard()
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при расчете стоимости склада: {str(e)}\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь к разработчику.",
            reply_markup=get_back_to_statistics_keyboard()
        )

    await callback.answer()


# Обработчик для возврата в меню статистики
@router.callback_query(F.data == "back_to_statistics")
async def back_to_statistics_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик для возврата в меню статистики"""
    await state.clear()
    await callback.message.edit_text(
        "📈 Меню статистики\n\n"
        "Выберите тип статистики для просмотра:",
        reply_markup=get_statistics_menu_keyboard()
    )
    await callback.answer()


# Обработчик для возврата в главное меню админа
@router.callback_query(F.data == "back_to_admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик для возврата в главное меню администратора"""
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 Панель управления администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


# Обработчик для статистики продаж
@router.callback_query(F.data == "sales_statistics")
async def show_sales_statistics(callback: CallbackQuery, state: FSMContext):
    """Обработчик для отображения статистики продаж"""
    await state.set_state(StatisticsState.sales_statistics)

    # Получаем общую статистику
    total_orders, total_sales, average_check, delivered_orders = get_total_sales_statistics()

    # Получаем данные о заказах для первой страницы
    orders, total_pages = get_delivered_orders(page=1)

    # Сохраняем данные в состоянии
    await state.update_data(current_page=1, total_pages=total_pages)

    # Формируем сообщение со статистикой
    message_text = (
        "📊 <b>Статистика продаж</b>\n\n"
        f"📦 Всего заказов: <b>{total_orders}</b>\n"
        f"✅ Доставлено заказов: <b>{delivered_orders}</b>\n"
        f"💰 Общая сумма продаж: <b>{total_sales:.2f} руб.</b>\n"
        f"🧾 Средний чек: <b>{average_check:.2f} руб.</b>\n\n"
    )

    if orders:
        message_text += "<b>Доставленные заказы:</b>\n\n"
        for order in orders:
            message_text += (
                f"<b>Заказ #{order['order_id']}</b> от {order['created_at']}\n"
                f"👤 Клиент: {order['name']} (ID: {order['user_id']})\n"
                f"📱 Телефон: {order['phone']}\n"
            )

            # Добавляем информацию о скидке (скидка в рублях, а не в процентах)
            discount_amount = order.get('discount_amount', 0)
            if discount_amount > 0:
                original_amount = order['total_amount'] + discount_amount
                discount_percent = round(discount_amount / original_amount * 100, 1)
                message_text += (
                    f"💵 Сумма: <s>{original_amount:.2f} руб.</s> → "
                    f"{order['total_amount']:.2f} руб. "
                    f"(-{discount_percent}%, -{discount_amount:.2f} руб.)\n"
                )
            else:
                message_text += f"💵 Сумма: {order['total_amount']:.2f} руб.\n"

            message_text += (
                f"📅 Дата доставки: {order['delivery_date']}\n"
                f"🕒 Время доставки: {order['delivery_time']}\n"
                f"📍 Адрес: {order['delivery_address']}\n"
                f"💳 Способ оплаты: {order['payment_method']}\n"
            )

            if order['comment']:
                message_text += f"💬 Комментарий: {order['comment']}\n"

            message_text += "📦 Товары:\n"
            for item in order['items']:
                message_text += f"   • {item['product_name']} - {item['quantity']} шт. × {item['price']} руб.\n"

            message_text += "\n"
    else:
        message_text += "Нет доставленных заказов.\n"

    # Отправляем сообщение с пагинацией
    await callback.message.edit_text(
        message_text,
        reply_markup=get_pagination_keyboard(1, total_pages, "sales"),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик для пагинации статистики продаж
@router.callback_query(F.data.startswith("sales_page_"))
async def paginate_sales_statistics(callback: CallbackQuery, state: FSMContext):
    """Обработчик для пагинации статистики продаж"""
    # Получаем запрошенную страницу
    page = int(callback.data.split("_")[-1])

    # Получаем общую статистику
    total_orders, total_sales, average_check, delivered_orders = get_total_sales_statistics()

    # Получаем данные о заказах для запрошенной страницы
    orders, total_pages = get_delivered_orders(page=page)

    # Обновляем данные в состоянии
    await state.update_data(current_page=page, total_pages=total_pages)

    # Формируем сообщение со статистикой
    message_text = (
        "📊 <b>Статистика продаж</b>\n\n"
        f"📦 Всего заказов: <b>{total_orders}</b>\n"
        f"✅ Доставлено заказов: <b>{delivered_orders}</b>\n"
        f"💰 Общая сумма продаж: <b>{total_sales:.2f} руб.</b>\n"
        f"🧾 Средний чек: <b>{average_check:.2f} руб.</b>\n\n"
    )

    if orders:
        message_text += "<b>Доставленные заказы:</b>\n\n"
        for order in orders:
            message_text += (
                f"<b>Заказ #{order['order_id']}</b> от {order['created_at']}\n"
                f"👤 Клиент: {order['name']} (ID: {order['user_id']})\n"
                f"📱 Телефон: {order['phone']}\n"
            )

            # Добавляем информацию о скидке (скидка в рублях, а не в процентах)
            discount_amount = order.get('discount_amount', 0)
            if discount_amount > 0:
                original_amount = order['total_amount'] + discount_amount
                discount_percent = round(discount_amount / original_amount * 100, 1)
                message_text += (
                    f"💵 Сумма: <s>{original_amount:.2f} руб.</s> → "
                    f"{order['total_amount']:.2f} руб. "
                    f"(-{discount_percent}%, -{discount_amount:.2f} руб.)\n"
                )
            else:
                message_text += f"💵 Сумма: {order['total_amount']:.2f} руб.\n"

            message_text += (
                f"📅 Дата доставки: {order['delivery_date']}\n"
                f"🕒 Время доставки: {order['delivery_time']}\n"
                f"📍 Адрес: {order['delivery_address']}\n"
                f"💳 Способ оплаты: {order['payment_method']}\n"
            )

            if order['comment']:
                message_text += f"💬 Комментарий: {order['comment']}\n"

            message_text += "📦 Товары:\n"
            for item in order['items']:
                message_text += f"   • {item['product_name']} - {item['quantity']} шт. × {item['price']} руб.\n"

            message_text += "\n"
    else:
        message_text += "Нет доставленных заказов.\n"

    # Отправляем сообщение с пагинацией
    await callback.message.edit_text(
        message_text,
        reply_markup=get_pagination_keyboard(page, total_pages, "sales"),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик для статистики прибыли
@router.callback_query(F.data == "profit_statistics")
async def show_profit_statistics(callback: CallbackQuery, state: FSMContext):
    """Обработчик для отображения статистики прибыли"""
    await state.set_state(StatisticsState.profit_statistics)

    # Получаем данные о прибыли для первой страницы
    profit_data, total_pages = get_profit_statistics(page=1)

    # Сохраняем данные в состоянии
    await state.update_data(current_page=1, total_pages=total_pages)

    # Формируем сообщение со статистикой прибыли
    message_text = "💹 <b>Статистика прибыли</b>\n\n"

    if profit_data:
        for order in profit_data:
            message_text += (
                f"<b>Заказ #{order['user_order_id']}</b> от {order['created_at']}\n"
                f"👤 Клиент: {order['name']} (ID: {order['user_id']})\n"
            )

            # Добавляем информацию о скидке (скидка в рублях, а не в процентах)
            discount_amount = order.get('discount_amount', 0)
            if discount_amount > 0:
                original_amount = order['revenue'] + discount_amount
                discount_percent = round(discount_amount / original_amount * 100, 1)
                message_text += (
                    f"💵 Выручка: <s>{original_amount:.2f} руб.</s> → "
                    f"{order['revenue']:.2f} руб. "
                    f"(-{discount_percent}%, -{discount_amount:.2f} руб.)\n"
                )
            else:
                message_text += f"💵 Выручка: {order['revenue']:.2f} руб.\n"

            message_text += (
                f"💰 Прибыль: {order['profit']:.2f} руб.\n"
                f"📊 Маржинальность: {order['margin']:.2f}%\n\n"
            )
    else:
        message_text += "Нет данных о прибыли.\n"

    # Отправляем сообщение с пагинацией
    await callback.message.edit_text(
        message_text,
        reply_markup=get_pagination_keyboard(1, total_pages, "profit"),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик для пагинации статистики прибыли
@router.callback_query(F.data.startswith("profit_page_"))
async def paginate_profit_statistics(callback: CallbackQuery, state: FSMContext):
    """Обработчик для пагинации статистики прибыли"""
    # Получаем запрошенную страницу
    page = int(callback.data.split("_")[-1])

    # Получаем данные о прибыли для запрошенной страницы
    profit_data, total_pages = get_profit_statistics(page=page)

    # Обновляем данные в состоянии
    await state.update_data(current_page=page, total_pages=total_pages)

    # Формируем сообщение со статистикой прибыли
    message_text = "💹 <b>Статистика прибыли</b>\n\n"

    if profit_data:
        for order in profit_data:
            message_text += (
                f"<b>Заказ #{order['user_order_id']}</b> от {order['created_at']}\n"
                f"👤 Клиент: {order['name']} (ID: {order['user_id']})\n"
            )

            # Добавляем информацию о скидке (скидка в рублях, а не в процентах)
            discount_amount = order.get('discount_amount', 0)
            if discount_amount > 0:
                original_amount = order['revenue'] + discount_amount
                discount_percent = round(discount_amount / original_amount * 100, 1)
                message_text += (
                    f"💵 Выручка: <s>{original_amount:.2f} руб.</s> → "
                    f"{order['revenue']:.2f} руб. "
                    f"(-{discount_percent}%, -{discount_amount:.2f} руб.)\n"
                )
            else:
                message_text += f"💵 Выручка: {order['revenue']:.2f} руб.\n"

            message_text += (
                f"💰 Прибыль: {order['profit']:.2f} руб.\n"
                f"📊 Маржинальность: {order['margin']:.2f}%\n\n"
            )
    else:
        message_text += "Нет данных о прибыли.\n"

    # Отправляем сообщение с пагинацией
    await callback.message.edit_text(
        message_text,
        reply_markup=get_pagination_keyboard(page, total_pages, "profit"),
        parse_mode="HTML"
    )
    await callback.answer()