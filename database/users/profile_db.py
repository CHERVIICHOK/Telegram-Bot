import sqlite3
from datetime import datetime
import logging

from database.users.database_connection import create_connection, close_connection
from database.users.warehouse_connection import create_connection_warehouse, close_connection_warehouse


def create_profile_tables():
    """Создание таблиц для личного кабинета"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                user_id INTEGER PRIMARY KEY,
                order_status_notifications BOOLEAN DEFAULT TRUE,
                notification_start_time TEXT DEFAULT '10:00',
                notification_end_time TEXT DEFAULT '22:00',
                notification_frequency TEXT DEFAULT 'daily'
            )
            ''')

            # Проверяем существование таблицы orders
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
            table_exists = cursor.fetchone()

            if not table_exists:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    status TEXT DEFAULT 'Принят на обработку',
                    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT,
                    delivery_address TEXT,
                    total_amount REAL,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
                ''')
            else:
                # Проверяем существование полей в таблице orders
                cursor.execute("PRAGMA table_info(orders)")
                columns = cursor.fetchall()
                column_names = [column[1] for column in columns]

                if 'status' not in column_names:
                    cursor.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Принят на обработку'")
                if 'created_at' not in column_names:
                    cursor.execute("ALTER TABLE orders ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            conn.commit()
            logging.info("Таблицы для личного кабинета успешно созданы.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблиц для личного кабинета: {e}")
        finally:
            close_connection(conn)


def init_notification_settings(user_id):
    """Инициализация настроек уведомлений для нового пользователя"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO notification_settings (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
            logging.info(f"Инициализированы настройки уведомлений для пользователя {user_id}")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при инициализации настроек: {e}")
        finally:
            close_connection(conn)


def get_notification_settings(user_id):
    """Получение настроек уведомлений пользователя"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM notification_settings WHERE user_id = ?",
                (user_id,)
            )
            settings = cursor.fetchone()
            if not settings:
                close_connection(conn)
                init_notification_settings(user_id)
                return get_notification_settings(user_id)

            return {
                'user_id': settings[0],
                'order_status_notifications': bool(settings[1]),
                'notification_start_time': settings[2],
                'notification_end_time': settings[3],
                'notification_frequency': settings[4]
            }
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении настроек: {e}")
            return None
        finally:
            close_connection(conn)
    return None


def update_notification_settings(user_id, settings):
    """Обновление настроек уведомлений пользователя"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE notification_settings 
                SET order_status_notifications = ?,
                    notification_start_time = ?,
                    notification_end_time = ?,
                    notification_frequency = ?
                WHERE user_id = ?
                """,
                (
                    settings.get('order_status_notifications', True),
                    settings.get('notification_start_time', '10:00'),
                    settings.get('notification_end_time', '22:00'),
                    settings.get('notification_frequency', 'daily'),
                    user_id
                )
            )
            conn.commit()
            logging.info(f"Обновлены настройки уведомлений для пользователя {user_id}")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении настроек: {e}")
        finally:
            close_connection(conn)


def disable_all_notifications(user_id):
    """Отключение всех уведомлений для пользователя"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE notification_settings SET order_status_notifications = 0 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            logging.info(f"Отключены все уведомления для пользователя {user_id}")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при отключении уведомлений: {e}")
        finally:
            close_connection(conn)


def get_active_orders(user_id):
    """Получение активных заказов пользователя (не доставленных)"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, status, created_at 
                FROM orders 
                WHERE user_id = ? AND status != 'Доставлен'
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            orders = cursor.fetchall()
            return orders
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении активных заказов: {e}")
            return []
        finally:
            close_connection(conn)
    return []


def get_all_orders(user_id):
    """Получение всех заказов пользователя"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, status, created_at, user_order_id
                FROM orders 
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            orders = cursor.fetchall()
            return orders
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении всех заказов: {e}")
            return []
        finally:
            close_connection(conn)
    return []


def get_order_details(order_id):
    """Получение детальной информации о заказе"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """  
                SELECT id, user_id, status, created_at,                       
                payment_method, delivery_address, user_order_id, discount   
                FROM orders   
                WHERE id = ?  
                """,
                (order_id,)
            )
            order = cursor.fetchone()

            if not order:
                return None

            cursor.execute(
                """  
                SELECT product_id, quantity, price                
                FROM order_items               
                WHERE order_id = ?                
                """,
                (order_id,)
            )
            items = cursor.fetchall()

            # Подключаемся к warehouse.db для получения информации о товарах
            warehouse_conn = create_connection_warehouse()
            if not warehouse_conn:
                return None

            enriched_items = []
            warehouse_cursor = warehouse_conn.cursor()

            for item in items:
                product_id, quantity, price = item

                # Получаем информацию о товаре из warehouse.db
                warehouse_cursor.execute(
                    """
                    SELECT product_full_name, description
                    FROM products
                    WHERE id = ?
                    """,
                    (product_id,)
                )
                product = warehouse_cursor.fetchone()

                if product:
                    name, description = product
                    enriched_items.append({
                        'product_id': product_id,
                        'name': name,
                        'description': description,
                        'quantity': quantity,
                        'price': price
                    })
                else:
                    # Если товар не найден, добавляем базовую информацию
                    enriched_items.append({
                        'product_id': product_id,
                        'name': "Товар не найден",
                        'description': "Нет информации",
                        'quantity': quantity,
                        'price': price
                    })

            # Вычисляем общую сумму заказа
            total_amount = sum(item['quantity'] * item['price'] for item in enriched_items)

            result = {
                'order_id': order[0],
                'user_id': order[1],
                'status': order[2],
                'creation_date': order[3],
                'payment_method': order[4],
                'delivery_address': order[5],
                'total_amount': total_amount,
                'items': enriched_items,
                'user_order_id': order[6],
                'discount': order[7]
            }

            close_connection_warehouse(warehouse_conn)
            return result

        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении деталей заказа: {e}")
            return None
        finally:
            close_connection(conn)
    return None


def get_product_info_from_order(order_id):
    """
    Получает информацию о товарах в заказе (flavor, product_name, product_full_name)
    из warehouse.db, основываясь на order_id в shop_bot.db.
    """
    conn_warehouse = create_connection_warehouse()
    if not conn_warehouse:
        return None

    conn_shop = create_connection()
    if not conn_shop:
        return None

    cursor_shop = conn_shop.cursor()

    try:
        cursor_shop.execute(
            """
            SELECT product_id
            FROM order_items
            WHERE order_id = ?
            """,
            (order_id,)
        )
        product_ids = cursor_shop.fetchall()

        if not product_ids:
            return None  # В заказе нет товаров

        product_info_list = []

        cursor_warehouse = conn_warehouse.cursor()

        for product_id_tuple in product_ids:
            product_id = product_id_tuple[0]  # Извлекаем product_id из кортежа

            cursor_warehouse.execute(
                """
                SELECT flavor, product_name, product_full_name
                FROM products
                WHERE id = ?
                """,
                (product_id,)
            )
            product_info = cursor_warehouse.fetchone()

            if product_info:
                flavor, product_name, product_full_name = product_info
                product_info_list.append({
                    'product_id': product_id,
                    'flavor': flavor,
                    'product_name': product_name,
                    'product_full_name': product_full_name
                })
            else:
                product_info_list.append({
                    'product_id': product_id,
                    'flavor': None,
                    'product_name': "Товар не найден",
                    'product_full_name': "Товар не найден"
                })

        return product_info_list

    except sqlite3.Error as e:
        print(f"Ошибка при получении информации о товаре из заказа: {e}")
        return None

    finally:
        if conn_warehouse:
            close_connection_warehouse(conn_warehouse)
        if conn_shop:
            close_connection(conn_shop)


def add_items_to_cart_from_order(user_id, order_id):
    """Добавление товаров из заказа в корзину для повторного заказа"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                (order_id,)
            )
            items = cursor.fetchall()

            # Очистка текущей корзины пользователя
            cursor.execute(
                "DELETE FROM cart WHERE user_id = ?",
                (user_id,)
            )

            # Добавление товаров в корзину
            for item in items:
                product_id, quantity = item
                cursor.execute(
                    "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                    (user_id, product_id, quantity)
                )

            conn.commit()
            logging.info(f"Товары из заказа {order_id} добавлены в корзину пользователя {user_id}")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении товаров в корзину: {e}")
        finally:
            close_connection(conn)


def update_order_status(order_id, new_status):
    """Обновление статуса заказа и получение ID пользователя для уведомления"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET status = ? WHERE order_id = ?",
                (new_status, order_id)
            )

            cursor.execute(
                "SELECT user_id FROM orders WHERE order_id = ?",
                (order_id,)
            )
            user_id = cursor.fetchone()

            conn.commit()
            logging.info(f"Обновлен статус заказа {order_id} на '{new_status}'")

            return user_id[0] if user_id else None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении статуса заказа: {e}")
            return None
        finally:
            close_connection(conn)
    return None


def should_send_notification(user_id):
    """Проверка, следует ли отправлять уведомление пользователю"""
    settings = get_notification_settings(user_id)

    if not settings or not settings['order_status_notifications']:
        return False

    # Проверка времени
    current_time = datetime.now().strftime('%H:%M')
    if settings['notification_start_time'] <= current_time <= settings['notification_end_time']:
        return True

    return False
