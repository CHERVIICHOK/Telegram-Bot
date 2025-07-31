import sqlite3
import datetime
from typing import List, Dict, Optional
from aiogram import Bot
import logging
from database.admins.staff_db import get_staff_by_role

from database.admins.stock_thresholds_db import (
    get_product_threshold,
    get_all_product_thresholds,
    update_last_notification_date,
    log_stock_notification,
    update_notification_delivered
)

logger = logging.getLogger(__name__)


async def check_low_stock_products(warehouse_conn: sqlite3.Connection, shop_conn: sqlite3.Connection, bot: Bot) -> None:
    """
    Проверяет все товары на наличие низких остатков и отправляет уведомления
    """
    # Получаем все товары с установленными порогами
    thresholds = get_all_product_thresholds(shop_conn)

    for product_id, threshold in thresholds:
        await check_product_stock(warehouse_conn, shop_conn, bot, product_id, threshold)


async def check_product_stock(
        warehouse_conn: sqlite3.Connection,
        shop_conn: sqlite3.Connection,
        bot: Bot,
        product_id: int,
        threshold: Optional[int] = None
) -> None:
    """
    Проверяет остаток конкретного товара и отправляет уведомление при необходимости
    """
    # Если порог не указан, получаем его из БД
    if threshold is None:
        threshold = get_product_threshold(shop_conn, product_id)
        if threshold is None:
            # Для этого товара не установлен порог
            return

    # Получаем информацию о товаре из warehouse_db
    cursor = warehouse_conn.cursor()
    cursor.execute(
        "SELECT id, category, product_name, product_full_name, flavor, quantity FROM products WHERE id = ?",
        (product_id,)
    )
    product = cursor.fetchone()

    if not product:
        logger.warning(f"Товар с ID {product_id} не найден в базе данных")
        return

    product_id, category, product_name, product_full_name, flavor, quantity = product

    # Проверяем, требуется ли отправка уведомления
    if quantity <= threshold:
        # Получаем данные о последних продажах товара
        recent_sales = get_recent_sales(shop_conn, product_id)

        # Формируем и отправляем уведомление
        await send_low_stock_notification(
            shop_conn,
            bot,
            product_id,
            product_full_name,
            quantity,
            threshold,
            recent_sales
        )


def get_recent_sales(conn: sqlite3.Connection, product_id: int, limit: int = 5) -> List[Dict]:
    """
    Получает информацию о последних продажах товара
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT oi.order_id, oi.quantity, oi.price, o.created_at
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE oi.product_id = ?
        ORDER BY o.created_at DESC
        LIMIT ?
        """,
        (product_id, limit)
    )

    sales = []
    for row in cursor.fetchall():
        order_id, quantity, price, creation_date = row
        sales.append({
            "order_id": order_id,
            "quantity": quantity,
            "price": price,
            "date": creation_date
        })

    return sales


async def send_low_stock_notification(
        conn: sqlite3.Connection,
        bot: Bot,
        product_id: int,
        product_name: str,
        current_stock: int,
        threshold: int,
        recent_sales: List[Dict]
) -> None:
    """
    Отправляет уведомление админу о низком остатке товара
    """
    # Формируем текст уведомления
    message_text = f"⚠️ <b>ВНИМАНИЕ! Низкий остаток товара</b>\n\n"
    message_text += f"<b>Товар:</b> {product_name}\n"
    message_text += f"<b>Текущий остаток:</b> {current_stock} шт.\n"
    message_text += f"<b>Установленный порог:</b> {threshold} шт.\n\n"

    if recent_sales:
        message_text += "<b>Последние продажи:</b>\n"
        total_sold = 0
        for sale in recent_sales:
            sale_date = datetime.datetime.fromisoformat(sale["date"]).strftime("%d.%m.%Y %H:%M")
            message_text += f"• Заказ #{sale['order_id']} - {sale_date}: {sale['quantity']} шт.\n"
            total_sold += sale["quantity"]

        message_text += f"\n<b>Всего продано за последнее время:</b> {total_sold} шт."
    else:
        message_text += "<i>Нет данных о последних продажах этого товара.</i>"

    # Логируем уведомление в БД
    notification_id = log_stock_notification(
        conn,
        product_id,
        product_name,
        current_stock,
        threshold
    )

    # Отправляем уведомление
    try:
        admins = get_staff_by_role(role="Админ")
        admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
        for admin_id in admin_ids:
            await bot.send_message(
                admin_id,
                message_text,
                parse_mode="HTML"
            )

        # Отмечаем уведомление как доставленное
        update_notification_delivered(conn, notification_id, True)

        # Обновляем дату последнего уведомления
        update_last_notification_date(conn, product_id)

        logger.info(f"Отправлено уведомление о низком остатке товара: {product_name}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о низком остатке: {e}")
