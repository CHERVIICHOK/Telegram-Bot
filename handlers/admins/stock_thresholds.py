from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from filters.admin_filter import AdminFilter
from states.stock_thresholds_state import StockThresholdState
from keyboards.admins.stock_thresholds_keyboard import (
    get_stock_threshold_menu_keyboard,
    get_categories_for_threshold_keyboard,
    get_products_for_threshold_keyboard,
    get_threshold_confirmation_keyboard,
    get_thresholds_list_keyboard,
    get_notification_log_keyboard
)
from utils.stock_notification_utils import (
    check_low_stock_products,
)
from database.admins.stock_thresholds_db import (
    create_stock_thresholds_table,
    set_product_threshold,
    get_product_threshold,
    get_all_product_thresholds,
    get_recent_notifications
)
from database.users.database_connection import create_connection
from database.users.warehouse_connection import create_connection_warehouse

import logging

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# Инициализация таблиц при запуске
def init_stock_thresholds_tables():
    """Инициализирует таблицы для порогов уведомлений о низком остатке товаров"""
    conn = create_connection()
    create_stock_thresholds_table(conn)
    conn.close()
    logger.info("Таблицы для порогов уведомлений о низком остатке товаров инициализированы")


# Обработчик для открытия меню настройки порогов уведомлений
@router.callback_query(F.data == "manage_stock_thresholds")
async def show_stock_threshold_menu(callback: CallbackQuery):
    """Показывает меню настройки порогов уведомлений"""
    await callback.message.edit_text(
        "🔔 <b>Управление уведомлениями о низком остатке товаров</b>\n\n"
        "Здесь вы можете настроить пороги уведомлений для товаров, просмотреть установленные пороги "
        "и вручную проверить товары с низким остатком.",
        reply_markup=get_stock_threshold_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик для возврата в меню настройки порогов
@router.callback_query(F.data == "back_to_threshold_menu")
async def back_to_threshold_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в меню настройки порогов"""
    await state.clear()
    await show_stock_threshold_menu(callback)


# Обработчик для выбора категории товара
@router.callback_query(F.data == "set_product_threshold")
async def choose_category_for_threshold(callback: CallbackQuery, state: FSMContext):
    """Показывает список категорий товаров для выбора"""
    wh_conn = create_connection_warehouse()
    cursor = wh_conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products WHERE is_active = 1")
    categories = [row[0] for row in cursor.fetchall()]
    wh_conn.close()

    await state.set_state(StockThresholdState.select_category)

    await callback.message.edit_text(
        "Выберите категорию товара для установки порога уведомления:",
        reply_markup=get_categories_for_threshold_keyboard(categories)
    )
    await callback.answer()


# Обработчик для возврата к выбору категории
@router.callback_query(F.data == "back_to_threshold_categories")
async def back_to_threshold_categories(callback: CallbackQuery, state: FSMContext):
    """Возвращает пользователя к выбору категории товара"""
    await choose_category_for_threshold(callback, state)


# Обработчик для выбора товара
@router.callback_query(StockThresholdState.select_category, F.data.startswith("threshold_category:"))
async def choose_product_for_threshold(callback: CallbackQuery, state: FSMContext):
    """Показывает список товаров в выбранной категории"""
    category = callback.data.split(":", 1)[1]

    wh_conn = create_connection_warehouse()
    cursor = wh_conn.cursor()
    cursor.execute(
        "SELECT id, product_full_name FROM products WHERE category = ? AND is_active = 1",
        (category,)
    )
    products = cursor.fetchall()
    wh_conn.close()

    await state.update_data(category=category)
    await state.set_state(StockThresholdState.select_product)

    await callback.message.edit_text(
        f"Выберите товар из категории <b>{category}</b> для установки порога уведомления:",
        reply_markup=get_products_for_threshold_keyboard(products, category),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик для ввода порога
@router.callback_query(StockThresholdState.select_product, F.data.startswith("threshold_product:"))
async def enter_threshold_value(callback: CallbackQuery, state: FSMContext):
    """Запрашивает у пользователя значение порога уведомления"""
    product_id = int(callback.data.split(":", 1)[1])

    wh_conn = create_connection_warehouse()
    cursor = wh_conn.cursor()
    cursor.execute("SELECT product_full_name, quantity FROM products WHERE id = ?", (product_id,))
    product_info = cursor.fetchone()
    wh_conn.close()

    if not product_info:
        await callback.message.edit_text(
            "❌ Ошибка: товар не найден. Попробуйте выбрать другой товар.",
            reply_markup=get_stock_threshold_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    product_name, current_stock = product_info

    # Проверяем, установлен ли уже порог для этого товара
    conn = create_connection()
    current_threshold = get_product_threshold(conn, product_id)
    conn.close()

    threshold_info = f"(текущий порог: {current_threshold})" if current_threshold is not None else ""

    await state.update_data(product_id=product_id, product_name=product_name, current_stock=current_stock)
    await state.set_state(StockThresholdState.enter_threshold)

    await callback.message.edit_text(
        f"Установка порога уведомления для товара:\n"
        f"<b>{product_name}</b>\n\n"
        f"Текущий остаток: <b>{current_stock}</b> шт.\n"
        f"{threshold_info}\n\n"
        f"Введите значение порога (целое число):",
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик для ввода значения порога
@router.message(StockThresholdState.enter_threshold)
async def process_threshold_value(message: Message, state: FSMContext):
    """Обрабатывает введенное значение порога и запрашивает подтверждение"""
    # Проверяем, что введено число
    try:
        threshold = int(message.text.strip())
        if threshold <= 0:
            raise ValueError("Значение должно быть положительным")
    except ValueError:
        await message.answer(
            "❌ Ошибка: введите положительное целое число."
        )
        return

    # Получаем данные о товаре из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    product_name = data.get("product_name")
    current_stock = data.get("current_stock")

    await state.update_data(threshold=threshold)
    await state.set_state(StockThresholdState.confirm_threshold)

    # Определяем статус остатка относительно порога
    stock_status = "❗️ НИЖЕ ПОРОГА ❗️" if current_stock <= threshold else "✅ выше порога"

    await message.answer(
        f"<b>Подтвердите установку порога уведомления:</b>\n\n"
        f"Товар: <b>{product_name}</b>\n"
        f"Текущий остаток: <b>{current_stock}</b> шт. ({stock_status})\n"
        f"Порог уведомления: <b>{threshold}</b> шт.\n\n"
        f"Вы получите уведомление, когда остаток товара станет равным или меньшим установленного порога.",
        reply_markup=get_threshold_confirmation_keyboard(product_id, threshold),
        parse_mode="HTML"
    )


# Обработчик для подтверждения установки порога
@router.callback_query(StockThresholdState.confirm_threshold, F.data.startswith("confirm_threshold:"))
async def confirm_threshold_setting(callback: CallbackQuery, state: FSMContext):
    """Устанавливает порог уведомления для товара"""
    _, product_id, threshold = callback.data.split(":", 2)
    product_id = int(product_id)
    threshold = int(threshold)

    data = await state.get_data()
    product_name = data.get("product_name")

    # Сохраняем порог в базе данных
    conn = create_connection()
    set_product_threshold(conn, product_id, threshold)
    conn.close()

    await callback.message.edit_text(
        f"✅ Порог уведомления для товара <b>{product_name}</b> установлен на <b>{threshold}</b> шт.",
        reply_markup=get_stock_threshold_menu_keyboard(),
        parse_mode="HTML"
    )

    await state.clear()
    await callback.answer()


# Обработчик для отмены установки порога
@router.callback_query(F.data == "cancel_threshold_setting")
async def cancel_threshold_setting(callback: CallbackQuery, state: FSMContext):
    """Отменяет установку порога уведомления"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Установка порога отменена.",
        reply_markup=get_stock_threshold_menu_keyboard()
    )
    await callback.answer()


# Обработчик для просмотра установленных порогов
@router.callback_query(F.data == "view_thresholds")
async def view_thresholds(callback: CallbackQuery):
    """Показывает список установленных порогов уведомлений"""
    shop_conn = create_connection()
    wh_conn = create_connection_warehouse()

    # Получаем список всех установленных порогов
    thresholds = get_all_product_thresholds(shop_conn)

    if not thresholds:
        await callback.message.edit_text(
            "ℹ️ Нет установленных порогов уведомлений.",
            reply_markup=get_stock_threshold_menu_keyboard()
        )
        await callback.answer()
        shop_conn.close()
        wh_conn.close()
        return

    # Получаем информацию о товарах
    threshold_info = []
    for product_id, threshold in thresholds:
        cursor = wh_conn.cursor()
        cursor.execute(
            "SELECT product_full_name, quantity FROM products WHERE id = ?",
            (product_id,)
        )
        product_info = cursor.fetchone()

        if product_info:
            product_name, quantity = product_info
            threshold_info.append((product_id, product_name, threshold, quantity))

    shop_conn.close()
    wh_conn.close()

    # Сортируем список так, чтобы товары с остатком ниже порога были вверху
    threshold_info.sort(key=lambda x: (x[3] > x[2], x[3]))

    await callback.message.edit_text(
        "📋 <b>Установленные пороги уведомлений</b>\n\n"
        "Список товаров с установленными порогами уведомлений. "
        "Товары с остатком ниже порога показаны вверху списка.\n\n"
        "Формат: Название товара (текущий остаток/порог)",
        reply_markup=get_thresholds_list_keyboard(threshold_info),
        parse_mode="HTML"
    )

    await callback.answer()


# Обработчик для пагинации списка порогов
@router.callback_query(F.data.startswith("threshold_page:"))
async def threshold_pagination(callback: CallbackQuery):
    """Обрабатывает навигацию по страницам списка порогов"""
    page = int(callback.data.split(":", 1)[1])

    shop_conn = create_connection()
    wh_conn = create_connection_warehouse()

    # Получаем список всех установленных порогов
    thresholds = get_all_product_thresholds(shop_conn)

    # Получаем информацию о товарах
    threshold_info = []
    for product_id, threshold in thresholds:
        cursor = wh_conn.cursor()
        cursor.execute(
            "SELECT product_full_name, quantity FROM products WHERE id = ?",
            (product_id,)
        )
        product_info = cursor.fetchone()

        if product_info:
            product_name, quantity = product_info
            threshold_info.append((product_id, product_name, threshold, quantity))

    shop_conn.close()
    wh_conn.close()

    # Сортируем список так, чтобы товары с остатком ниже порога были вверху
    threshold_info.sort(key=lambda x: (x[3] > x[2], x[3]))

    await callback.message.edit_text(
        "📋 <b>Установленные пороги уведомлений</b>\n\n"
        "Список товаров с установленными порогами уведомлений. "
        "Товары с остатком ниже порога показаны вверху списка.\n\n"
        "Формат: Название товара (текущий остаток/порог)",
        reply_markup=get_thresholds_list_keyboard(threshold_info, page),
        parse_mode="HTML"
    )

    await callback.answer()


# Обработчик для редактирования порога
@router.callback_query(F.data.startswith("edit_threshold:"))
async def edit_threshold(callback: CallbackQuery, state: FSMContext):
    """Открывает форму редактирования порога для выбранного товара"""
    product_id = int(callback.data.split(":", 1)[1])

    wh_conn = create_connection_warehouse()
    cursor = wh_conn.cursor()
    cursor.execute("SELECT product_full_name, quantity FROM products WHERE id = ?", (product_id,))
    product_info = cursor.fetchone()
    wh_conn.close()

    if not product_info:
        await callback.message.edit_text(
            "❌ Ошибка: товар не найден. Возможно, он был удален.",
            reply_markup=get_stock_threshold_menu_keyboard()
        )
        await callback.answer()
        return

    product_name, current_stock = product_info

    # Получаем текущий порог
    conn = create_connection()
    current_threshold = get_product_threshold(conn, product_id)
    conn.close()

    await state.update_data(product_id=product_id, product_name=product_name, current_stock=current_stock)
    await state.set_state(StockThresholdState.enter_threshold)

    await callback.message.edit_text(
        f"Редактирование порога уведомления для товара:\n"
        f"<b>{product_name}</b>\n\n"
        f"Текущий остаток: <b>{current_stock}</b> шт.\n"
        f"Текущий порог: <b>{current_threshold}</b> шт.\n\n"
        f"Введите новое значение порога (целое число):",
        parse_mode="HTML"
    )

    await callback.answer()


# Обработчик для проверки товаров с низким остатком
@router.callback_query(F.data == "check_low_stock")
async def check_low_stock(callback: CallbackQuery):
    """Проверяет все товары с установленными порогами на низкий остаток"""
    await callback.answer("Проверяем товары с низким остатком...")

    shop_conn = create_connection()
    wh_conn = create_connection_warehouse()

    # Запускаем проверку всех товаров
    await check_low_stock_products(wh_conn, shop_conn, callback.bot)

    await callback.message.edit_text(
        "✅ Проверка товаров с низким остатком выполнена.\n"
        "Если найдены товары с остатком ниже порога, "
        "уведомления были отправлены всем администраторам.",
        reply_markup=get_stock_threshold_menu_keyboard()
    )

    shop_conn.close()
    wh_conn.close()


# Обработчик для просмотра журнала уведомлений
@router.callback_query(F.data == "view_notification_log")
async def view_notification_log(callback: CallbackQuery):
    """Показывает журнал уведомлений о низком остатке товаров"""
    conn = create_connection()

    # Получаем последние уведомления
    notifications = get_recent_notifications(conn, limit=5)
    conn.close()

    if not notifications:
        await callback.message.edit_text(
            "ℹ️ Журнал уведомлений пуст.",
            reply_markup=get_stock_threshold_menu_keyboard()
        )
        await callback.answer()
        return

    # Формируем текст с уведомлениями
    log_text = "📜 <b>Журнал уведомлений о низком остатке</b>\n\n"

    for notification in notifications:
        delivery_status = "✅ доставлено" if notification["delivered"] else "❌ не доставлено"
        notification_time = notification["notification_time"].split("T")[0]  # Упрощаем дату

        log_text += (
            f"<b>{notification_time}</b> - {notification['product_name']}\n"
            f"Остаток: {notification['current_stock']}/{notification['threshold']} ({delivery_status})\n\n"
        )

    await callback.message.edit_text(
        log_text,
        reply_markup=get_notification_log_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# Обработчик для пагинации журнала уведомлений
@router.callback_query(F.data.startswith("notification_log_page:"))
async def notification_log_pagination(callback: CallbackQuery):
    """Обрабатывает навигацию по страницам журнала уведомлений"""
    page = int(callback.data.split(":", 1)[1])

    # Проверяем, чтобы страница не была отрицательной
    if page < 0:
        page = 0
        await callback.answer("Вы на первой странице")
        return

    conn = create_connection()

    # Получаем уведомления для указанной страницы
    notifications = get_recent_notifications(conn, limit=5, offset=page * 5)
    conn.close()

    if not notifications and page > 0:
        # Если страница пуста и это не первая страница, вернемся на предыдущую
        await callback.answer("Достигнут конец списка")
        return

    if not notifications:
        await callback.message.edit_text(
            "ℹ️ Журнал уведомлений пуст.",
            reply_markup=get_stock_threshold_menu_keyboard()
        )
        await callback.answer()
        return

    # Формируем текст с уведомлениями
    log_text = "📜 <b>Журнал уведомлений о низком остатке</b>\n\n"

    for notification in notifications:
        delivery_status = "✅ доставлено" if notification["delivered"] else "❌ не доставлено"
        notification_time = notification["notification_time"].split("T")[0]  # Упрощаем дату

        log_text += (
            f"<b>{notification_time}</b> - {notification['product_name']}\n"
            f"Остаток: {notification['current_stock']}/{notification['threshold']} ({delivery_status})\n\n"
        )

    await callback.message.edit_text(
        log_text,
        reply_markup=get_notification_log_keyboard(page),
        parse_mode="HTML"
    )

    await callback.answer()


# Обработчик для возврата в админское меню
@router.callback_query(F.data == "back_to_admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в главное меню администратора"""
    from keyboards.admins.menu_keyboard import get_admin_menu_keyboard

    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
