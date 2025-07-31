import logging
import sqlite3
from database.users.database_connection import create_connection, close_connection
from config import DATABASE_NAME

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Возвращает соединение с базой данных.
    """
    return create_connection()


def add_to_cart(user_id, product_id, quantity=1):
    """
    Добавляет товар в корзину пользователя.
    Если товар уже есть в корзине, увеличивает его количество.
    """
    logger.info(f"Попытка добавить товар: user_id={user_id}, product_id={product_id}, quantity={quantity}")
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # Проверяем, создана ли таблица корзины
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        )
        ''')

        # Проверяем, есть ли уже этот товар в корзине пользователя
        cursor.execute(
            "SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        )
        existing_item = cursor.fetchone()

        if existing_item:
            # Товар уже есть в корзине, увеличиваем количество
            new_quantity = existing_item[0] + quantity
            cursor.execute(
                "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
                (new_quantity, user_id, product_id)
            )
        else:
            # Товара нет в корзине, добавляем новую запись
            cursor.execute(
                "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                (user_id, product_id, quantity)
            )
        logger.info(f"Результат добавления: {existing_item}")
        logger.info(existing_item)
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при добавлении товара в корзину: {e}")
        return False

    finally:
        close_connection(conn)


def get_cart_items(user_id):
    """
    Получает список товаров в корзине пользователя,
    соединяя данные из таблицы корзины и таблицы товаров.
    """
    conn = create_connection()
    cart_items = []

    if conn:
        try:
            cursor = conn.cursor()

            # Подключаемся к базе данных с товарами
            warehouse_conn = sqlite3.connect(DATABASE_NAME)
            warehouse_cursor = warehouse_conn.cursor()

            # Получаем информацию о товарах в корзине
            cursor.execute(
                "SELECT product_id, quantity FROM cart WHERE user_id = ?",
                (user_id,)
            )
            user_cart = cursor.fetchall()

            for product_id, quantity in user_cart:
                # Получаем информацию о товаре из базы данных товаров
                warehouse_cursor.execute(
                    "SELECT category, product_name, product_full_name, flavor, price FROM products WHERE id = ?",
                    (product_id,)
                )
                product_info = warehouse_cursor.fetchone()

                if product_info:
                    category, product_name, product_full_name, flavor, price = product_info
                    cart_items.append({
                        'category': category,
                        'product_id': product_id,
                        'product_full_name': product_full_name,
                        'product_name': product_name,
                        'flavor': flavor,
                        'price': price,
                        'quantity': quantity,
                        'total_price': price * quantity
                    })

            warehouse_conn.close()

        except sqlite3.Error as e:
            print(f"Ошибка при получении товаров из корзины: {e}")

        finally:
            close_connection(conn)

    return cart_items


def update_cart_item_quantity(user_id, product_id, quantity):
    """
    Обновляет количество товара в корзине.
    Если quantity = 0, товар удаляется из корзины.
    """
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        if quantity <= 0:
            # Удаляем товар из корзины
            cursor.execute(
                "DELETE FROM cart WHERE user_id = ? AND product_id = ?",
                (user_id, product_id)
            )
        else:
            # Обновляем количество
            cursor.execute(
                "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
                (quantity, user_id, product_id)
            )

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при обновлении корзины: {e}")
        return False

    finally:
        close_connection(conn)


def clear_cart(user_id):
    """Очищает корзину пользователя."""
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при очистке корзины: {e}")
        return False

    finally:
        close_connection(conn)


def create_orders_table(conn):
    """Создает таблицы для хранения заказов"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        delivery_date TEXT NOT NULL,
        delivery_time TEXT NOT NULL,
        delivery_type TEXT NOT NULL,
        delivery_address TEXT,
        payment_method TEXT NOT NULL,
        comment TEXT,
        status TEXT NOT NULL DEFAULT 'processing',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_order_id INTEGER,
        discount REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users(telegram_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS incomplete_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        state TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(telegram_id)
    )
    ''')
    conn.commit()


def save_order(conn, user_id, name, phone, delivery_date, delivery_time,
               delivery_type, delivery_address, payment_method, comment):
    """Сохраняет заказ в БД и возвращает ID заказа и номер заказа пользователя"""
    cursor = conn.cursor()

    # Получаем текущее количество заказов у данного пользователя
    cursor.execute('''
    SELECT COUNT(*) FROM orders WHERE user_id = ?
    ''', (user_id,))

    # Увеличиваем на 1 для нового заказа
    user_order_count = cursor.fetchone()[0] + 1

    # Вставляем заказ с номером пользователя
    cursor.execute('''
    INSERT INTO orders (user_id, user_order_id, name, phone, delivery_date, delivery_time, 
                       delivery_type, delivery_address, payment_method, comment)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, user_order_count, name, phone, delivery_date, delivery_time,
          delivery_type, delivery_address, payment_method, comment))

    conn.commit()
    global_order_id = cursor.lastrowid

    return [global_order_id, user_order_count]


def get_special_user_id(order_id):
    """Возвращает user_order_id из таблицы orders по указанному order_id"""
    conn = create_connection()

    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
            SELECT user_order_id FROM orders WHERE id = ?
            ''', (order_id,))

            result = cursor.fetchone()

            if result:
                return result[0]
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении уникального user_order_id: {e}")
            return []
        finally:
            close_connection(conn)
    return []


def save_order_item(conn, order_id, product_id, quantity, price):
    """Сохраняет элемент заказа в БД"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO order_items (order_id, product_id, quantity, price)
    VALUES (?, ?, ?, ?)
    ''', (order_id, product_id, quantity, price))
    conn.commit()


def save_incomplete_order(conn, user_id, state, data):
    """Сохраняет данные незавершенного заказа"""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM incomplete_orders WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    import json
    data_json = json.dumps(data)

    if result:
        cursor.execute('''
        UPDATE incomplete_orders 
        SET state = ?, data = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        ''', (state, data_json, user_id))
    else:
        cursor.execute('''
        INSERT INTO incomplete_orders (user_id, state, data)
        VALUES (?, ?, ?)
        ''', (user_id, state, data_json))

    conn.commit()


def get_incomplete_order(conn, user_id):
    """Получает данные незавершенного заказа"""
    cursor = conn.cursor()
    cursor.execute('''
    SELECT state, data FROM incomplete_orders 
    WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()

    if result:
        import json
        state, data_json = result
        data = json.loads(data_json)
        return state, data

    return None, None


def delete_incomplete_order(conn, user_id):
    """Удаляет незавершенный заказ"""
    cursor = conn.cursor()
    cursor.execute('DELETE FROM incomplete_orders WHERE user_id = ?', (user_id,))
    conn.commit()


def get_order_history(conn, user_id):
    """Получает историю заказов пользователя"""
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, name, phone, delivery_date, delivery_time, delivery_type, delivery_address, 
           payment_method, comment, status, created_at
    FROM orders
    WHERE user_id = ?
    ORDER BY created_at DESC
    ''', (user_id,))
    return cursor.fetchall()


def set_order_discount(order_id, discount):
    """
    Устанавливает Вкус скидки для конкретного заказа

    Параметры:
    conn - соединение с базой данных
    order_id - ID заказа, для которого устанавливается скидка
    discount - Вкус скидки (число)
    """

    conn = create_connection()

    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE orders 
                SET discount = ? 
                WHERE id = ?
                ''', (discount, order_id))
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Ошибка при соединении с shop_bot.db: {e}")
            return []
        finally:
            close_connection(conn)
    return []


def get_product_category(product_full_name):
    """
    Функция для получения категории товара по его полному имени из базы данных warehouse.db

    Args:
        product_full_name (str): Полное имя товара

    Returns:
        str: Категория товара или None, если товар не найден
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT category FROM products WHERE product_full_name = ?", (product_full_name,))
        result = cursor.fetchone()

        conn.close()

        return result[0] if result else None

    except sqlite3.Error as e:
        print(f"Ошибка SQLite: {e}")
        return None