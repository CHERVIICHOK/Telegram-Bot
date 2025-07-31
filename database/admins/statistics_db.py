import sqlite3
from typing import List, Dict, Tuple, Any


def get_total_sales_statistics() -> Tuple[int, float, float, int]:
    """
    Получает общую статистику продаж.

    Returns:
        Tuple[int, float, float, int]: (общее_количество_заказов, общая_сумма_продаж,
                                       средний_чек, количество_доставленных_заказов)
    """
    conn = sqlite3.connect('shop_bot.db')
    cursor = conn.cursor()

    # Общее количество заказов
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    # Количество доставленных заказов
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'delivered'")
    delivered_orders = cursor.fetchone()[0]

    # Общая сумма продаж с учетом скидки (discount - абсолютное значение в рублях)
    cursor.execute("""
        SELECT SUM(
            (SELECT SUM(quantity * price) FROM order_items WHERE order_id = o.id) - COALESCE(o.discount, 0)
        )
        FROM orders o
        WHERE o.status = 'delivered'
    """)
    total_sales = cursor.fetchone()[0] or 0

    # Средний чек
    average_check = total_sales / delivered_orders if delivered_orders > 0 else 0

    conn.close()

    return total_orders, total_sales, average_check, delivered_orders


def get_delivered_orders(page: int, page_size: int = 5) -> Tuple[List[Dict[str, Any]], int]:
    """
    Получает информацию о доставленных заказах с пагинацией.

    Args:
        page (int): Номер страницы
        page_size (int): Количество заказов на странице

    Returns:
        Tuple[List[Dict[str, Any]], int]: (список_заказов, общее_количество_страниц)
    """
    shop_conn = sqlite3.connect('shop_bot.db')
    shop_conn.row_factory = sqlite3.Row
    shop_cursor = shop_conn.cursor()

    # Подключение к базе данных склада для получения информации о товарах
    warehouse_conn = sqlite3.connect('warehouse.db')
    warehouse_conn.row_factory = sqlite3.Row
    warehouse_cursor = warehouse_conn.cursor()

    # Получаем общее количество доставленных заказов
    shop_cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'delivered'")
    total_orders = shop_cursor.fetchone()[0]

    # Рассчитываем общее количество страниц
    total_pages = (total_orders + page_size - 1) // page_size if total_orders > 0 else 1

    # Получаем информацию о заказах с пагинацией (добавлен discount)
    offset = (page - 1) * page_size
    shop_cursor.execute("""
        SELECT id as order_id, user_id, name, phone, delivery_date, delivery_time, 
               delivery_address, payment_method, comment, created_at, id, discount
        FROM orders 
        WHERE status = 'delivered'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (page_size, offset))

    orders = []
    for order in shop_cursor.fetchall():
        order_dict = dict(order)
        order_id = order_dict['order_id']
        discount = order_dict.get('discount', 0) or 0  # Абсолютное значение в рублях

        # Получаем товары для этого заказа
        shop_cursor.execute("""
            SELECT product_id, quantity, price
            FROM order_items
            WHERE order_id = ?
        """, (order_id,))

        items = []
        total_amount = 0

        for item in shop_cursor.fetchall():
            item_dict = dict(item)
            product_id = item_dict['product_id']
            quantity = item_dict['quantity']
            price = item_dict['price']

            # Получаем название товара из базы данных склада
            warehouse_cursor.execute("""
                SELECT product_full_name
                FROM products
                WHERE id = ?
            """, (product_id,))

            product_result = warehouse_cursor.fetchone()
            product_name = product_result['product_full_name'] if product_result else f"Товар #{product_id}"

            # Учет стоимости
            item_total = quantity * price
            total_amount += item_total

            items.append({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'price': price
            })

        # Применяем скидку как абсолютное значение
        total_amount_with_discount = max(0, total_amount - discount)

        # Рассчитываем процент скидки от исходной суммы
        discount_percent = round(discount / total_amount * 100, 1) if total_amount > 0 else 0

        order_dict['items'] = items
        order_dict['total_amount'] = total_amount_with_discount
        order_dict['original_amount'] = total_amount
        order_dict['discount_percent'] = discount_percent
        order_dict['discount_amount'] = discount

        orders.append(order_dict)

    shop_conn.close()
    warehouse_conn.close()

    return orders, total_pages


def get_profit_statistics(page: int, page_size: int = 5) -> Tuple[List[Dict[str, Any]], int]:
    """
    Получает статистику прибыли по заказам с пагинацией.

    Args:
        page (int): Номер страницы
        page_size (int): Количество заказов на странице

    Returns:
        Tuple[List[Dict[str, Any]], int]: (список_с_прибылью, общее_количество_страниц)
    """
    shop_conn = sqlite3.connect('shop_bot.db')
    shop_conn.row_factory = sqlite3.Row
    shop_cursor = shop_conn.cursor()

    # Получаем общее количество доставленных заказов
    shop_cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'delivered'")
    total_orders = shop_cursor.fetchone()[0]

    # Рассчитываем общее количество страниц
    total_pages = (total_orders + page_size - 1) // page_size if total_orders > 0 else 1

    # Получаем заказы с пагинацией (добавлен discount)
    offset = (page - 1) * page_size
    shop_cursor.execute("""
        SELECT id, user_order_id, name, user_id, created_at, discount
        FROM orders 
        WHERE status = 'delivered'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (page_size, offset))

    orders_data = []
    for order in shop_cursor.fetchall():
        order_dict = dict(order)
        order_id = order_dict['id']
        discount = order_dict.get('discount', 0) or 0  # Абсолютное значение в рублях

        # Получаем детали заказа для расчета выручки
        shop_cursor.execute("""
            SELECT product_id, quantity, price
            FROM order_items
            WHERE order_id = ?
        """, (order_id,))

        total_revenue_before_discount = 0
        items = []

        for item in shop_cursor.fetchall():
            item_dict = dict(item)
            quantity = item_dict['quantity']
            price = item_dict['price']
            total_revenue_before_discount += quantity * price
            items.append(item_dict)

        # Применяем скидку как абсолютное значение
        total_revenue = max(0, total_revenue_before_discount - discount)

        # Рассчитываем процент скидки от исходной суммы
        discount_percent = round(discount / total_revenue_before_discount * 100,
                                 1) if total_revenue_before_discount > 0 else 0

        # В данной реализации мы предполагаем, что прибыль равна выручке,
        # так как у нас нет информации о себестоимости
        profit = total_revenue
        margin = 100  # Маржинальность 100% как условный показатель

        orders_data.append({
            'order_id': order_id,
            'user_order_id': order_dict['user_order_id'],
            'name': order_dict['name'],
            'user_id': order_dict['user_id'],
            'created_at': order_dict['created_at'],
            'revenue_before_discount': total_revenue_before_discount,
            'discount_percent': discount_percent,
            'discount_amount': discount,
            'revenue': total_revenue,
            'profit': profit,
            'margin': margin,
            'items': items
        })

    shop_conn.close()

    return orders_data, total_pages
