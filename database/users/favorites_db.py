import sqlite3
from datetime import datetime
from database.users.database_connection import create_connection, close_connection
from database.users.warehouse_connection import create_connection_warehouse, close_connection_warehouse


def create_favorites_table():
    """Создание таблицы избранного если она не существует"""
    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            added_date DATETIME NOT NULL,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
            UNIQUE(telegram_id, product_id)
        )
        ''')
        conn.commit()
    finally:
        close_connection(conn)


def get_user_favorites(telegram_id: int):
    """Получение списка избранных товаров пользователя"""
    create_favorites_table()

    conn = create_connection()
    warehouse_conn = create_connection_warehouse()

    try:
        cursor = conn.cursor()
        warehouse_cursor = warehouse_conn.cursor()

        cursor.execute('''
        SELECT product_id FROM favorites
        WHERE telegram_id = ?
        ORDER BY added_date DESC
        ''', (telegram_id,))

        favorite_ids = [row[0] for row in cursor.fetchall()]

        if not favorite_ids:
            return []

        favorites_data = []
        for product_id in favorite_ids:
            warehouse_cursor.execute('''
            SELECT id, category, product_name, product_full_name, flavor, price, description, quantity, image_path, is_active
            FROM products
            WHERE id = ?
            ''', (product_id,))

            product = warehouse_cursor.fetchone()
            if product:
                favorites_data.append(product)

        return favorites_data
    finally:
        close_connection(conn)
        close_connection_warehouse(warehouse_conn)


def is_product_in_favorites(telegram_id: int, product_id: int) -> bool:
    """Проверка наличия товара в избранном пользователя"""
    create_favorites_table()

    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) FROM favorites
        WHERE telegram_id = ? AND product_id = ?
        ''', (telegram_id, product_id))

        count = cursor.fetchone()[0]
        return count > 0
    finally:
        close_connection(conn)


def add_product_to_favorites(telegram_id: int, product_id: int) -> bool:
    """Добавление товара в избранное пользователя"""
    create_favorites_table()

    # Проверяем существование товара на складе
    warehouse_conn = create_connection_warehouse()
    try:
        warehouse_cursor = warehouse_conn.cursor()
        warehouse_cursor.execute('''
        SELECT id FROM products
        WHERE id = ? AND is_active = 1
        ''', (product_id,))

        if not warehouse_cursor.fetchone():
            return False  # Товар не существует или не активен
    finally:
        close_connection_warehouse(warehouse_conn)

    # Добавляем в избранное
    conn = create_connection()
    try:
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Используем INSERT OR IGNORE для обработки уникальных ограничений
        cursor.execute('''
        INSERT OR IGNORE INTO favorites (telegram_id, product_id, added_date)
        VALUES (?, ?, ?)
        ''', (telegram_id, product_id, current_time))

        conn.commit()
        return cursor.rowcount > 0 or is_product_in_favorites(telegram_id, product_id)
    except sqlite3.Error:
        return False
    finally:
        close_connection(conn)


def remove_product_from_favorites(telegram_id: int, product_id: int) -> bool:
    """Удаление товара из избранного пользователя"""
    create_favorites_table()

    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        DELETE FROM favorites
        WHERE telegram_id = ? AND product_id = ?
        ''', (telegram_id, product_id))

        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        close_connection(conn)


def get_product_by_id(product_id: int):
    """Получение данных товара по ID"""
    conn = create_connection_warehouse()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, category, product_name, product_full_name, flavor, price, description, quantity, image_path, is_active
        FROM products
        WHERE id = ?
        ''', (product_id,))

        return cursor.fetchone()
    finally:
        close_connection_warehouse(conn)
