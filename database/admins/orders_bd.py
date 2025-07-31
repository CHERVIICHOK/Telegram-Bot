import sqlite3
import logging
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


def get_db_connection():
    """Создает и возвращает соединение с БД."""
    conn = sqlite3.connect('shop_bot.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_orders_by_status_category(category_key: str, page: int, per_page: int = 7) -> Tuple[List[Dict[str, Any]], int]:
    """
    Получает список заказов, соответствующих определенной категории статусов, с пагинацией.
    Args:
        category_key: Ключ категории статусов
        page: Номер страницы (начиная с 1)
        per_page: Количество заказов на странице
    Returns:
        Tuple со списком заказов и общим количеством заказов в категории
    """
    from utils.status_utils import STATUS_CATEGORIES

    # Получаем статусы для выбранной категории
    if category_key not in STATUS_CATEGORIES:
        logger.error(f"Unknown status category: {category_key}")
        return [], 0

    statuses = STATUS_CATEGORIES[category_key]["statuses"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Создаем параметры для запроса
        placeholders = ', '.join(['?' for _ in statuses])

        # Получаем общее количество заказов в категории
        query = f"SELECT COUNT(*) FROM orders WHERE status IN ({placeholders})"
        cursor.execute(query, statuses)
        total_orders = cursor.fetchone()[0]

        # Получаем список заказов для текущей страницы
        offset = (page - 1) * per_page
        query = f"SELECT id, status FROM orders WHERE status IN ({placeholders}) ORDER BY id DESC LIMIT ? OFFSET ?"
        params = statuses + [per_page, offset]
        cursor.execute(query, params)
        orders = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return orders, total_orders
    except Exception as e:
        logger.error(f"Error getting orders by status category {category_key}: {e}")
        return [], 0


def get_undelivered_orders(page: int, per_page: int = 7) -> Tuple[List[Dict[str, Any]], int]:
    """
    Получает список заказов, которые еще не доставлены, с пагинацией.

    Args:
        page: Номер страницы (начиная с 1)
        per_page: Количество заказов на странице

    Returns:
        Tuple со списком заказов и общим количеством недоставленных заказов
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем общее количество недоставленных заказов
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status != 'delivered'")
        total_orders = cursor.fetchone()[0]

        # Получаем список заказов для текущей страницы
        offset = (page - 1) * per_page
        cursor.execute(
            "SELECT id, status FROM orders WHERE status != 'delivered' ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        )
        orders = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return orders, total_orders
    except Exception as e:
        logger.error(f"Error getting undelivered orders: {e}")
        return [], 0


def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает информацию о заказе по его ID.

    Args:
        order_id: ID заказа

    Returns:
        Словарь с информацией о заказе или None, если заказ не найден
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()

        conn.close()

        if order:
            return dict(order)
        return None
    except Exception as e:
        logger.error(f"Error getting order by ID {order_id}: {e}")
        return None


def update_order_status(order_id: int, status: str) -> bool:
    """
    Обновляет статус заказа.

    Args:
        order_id: ID заказа
        status: Новый статус заказа

    Returns:
        True если обновление прошло успешно, иначе False
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()

        success = cursor.rowcount > 0
        conn.close()

        return success
    except Exception as e:
        logger.error(f"Error updating order status for order ID {order_id}: {e}")
        return False


def get_delivered_orders(page=1, per_page=7):
    """
    Получает список доставленных заказов с пагинацией.

    Args:
        page: Номер страницы
        per_page: Количество элементов на странице

    Returns:
        Tuple (orders, total_orders) - список заказов на указанной странице и общее количество
    """
    # Здесь должен быть код для получения заказов со статусом "delivered"
    # Пример реализации (замените на свой код)
    offset = (page - 1) * per_page
    # Замените на обращение к вашей БД
    delivered_orders = []  # Запрос к БД для получения доставленных заказов
    total_delivered = 0  # Запрос к БД для получения общего количества доставленных заказов

    return delivered_orders, total_delivered


def get_all_orders(page=1, per_page=7):
    """
    Получает список всех заказов с пагинацией.

    Args:
        page: Номер страницы
        per_page: Количество элементов на странице

    Returns:
        Tuple (orders, total_orders) - список заказов на указанной странице и общее количество
    """
    # Здесь должен быть код для получения всех заказов
    # Пример реализации (замените на свой код)
    offset = (page - 1) * per_page
    # Замените на обращение к вашей БД
    all_orders = []  # Запрос к БД для получения всех заказов
    total_orders = 0  # Запрос к БД для получения общего количества заказов

    return all_orders, total_orders


def delete_order_by_id(order_id: int) -> bool:
    """
    Удаляет заказ из базы данных по его ID.

    Args:
        order_id: ID заказа для удаления

    Returns:
        True если удаление прошло успешно, иначе False
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()

        success = cursor.rowcount > 0
        conn.close()

        if success:
            logger.info(f"Заказ с ID {order_id} успешно удален")
        else:
            logger.warning(f"Заказ с ID {order_id} не найден")

        return success
    except Exception as e:
        logger.error(f"Error deleting order with ID {order_id}: {e}")
        return False

