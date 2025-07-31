import logging
import sqlite3
from typing import Optional, Tuple

from config import DATABASE_NAME

logger = logging.getLogger(__name__)


def create_connection_warehouse():
    """Создает соединение с базой данных warehouse.db."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        logger.info(f"Подключение к базе данных {DATABASE_NAME} установлено.")
    except sqlite3.Error as e:
        print(f"Ошибка подключения к базе данных {DATABASE_NAME}: {e}")
    return conn


def close_connection_warehouse(conn):
    """Закрывает соединение с базой данных warehouse.db."""
    if conn:
        try:
            conn.close()
            logger.info(f"Соединение с базой данных {DATABASE_NAME} закрыто.")
        except sqlite3.Error as e:
            print(f"Ошибка при закрытии соединения с базой данных {DATABASE_NAME}: {e}")


def create_product_images_table(conn):
    """Функция для создания таблицы product_images"""
    cursor = conn.cursor()

    # Создаем таблицу product_images
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT UNIQUE,
        image_absolute_path TEXT,
        category TEXT,
        upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        file_size INTEGER,
        content_type TEXT
    )
    ''')

    conn.commit()
    conn.close()

    print("Таблица product_images успешно создана!")


def fetch_categories():
    """Получает список уникальных категорий товаров из базы данных."""
    conn = create_connection_warehouse()
    categories = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT category FROM products")
            rows = cursor.fetchall()
            categories = [row[0] for row in rows]
        except sqlite3.Error as e:
            print(f"Ошибка при запросе категорий: {e}")
        finally:
            close_connection_warehouse(conn)
    return categories


def fetch_product_names_by_category(category_name):
    """Получает список уникальных product_name для заданной категории."""
    conn = create_connection_warehouse()
    product_names = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT DISTINCT product_name FROM products WHERE category = ?",
                (category_name,)
            )
            rows = cursor.fetchall()
            product_names = [row[0] for row in rows]
        except sqlite3.Error as e:
            print(f"Ошибка при запросе названий товаров: {e}")
        finally:
            close_connection_warehouse(conn)
    return product_names


def fetch_products_by_category_and_product_name(category_name, product_name):
    """Получает список товаров для заданной категории и product_name."""
    conn = create_connection_warehouse()
    products = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT product_full_name, flavor, price, id, description, quantity, image_path FROM products "
                "WHERE category = ? AND product_name = ?",
                (category_name, product_name)
            )
            products = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка при запросе товаров: {e}")
        finally:
            close_connection_warehouse(conn)
    return products


def get_product_by_id(product_id):
    """Получает информацию о товаре по его ID."""
    conn = create_connection_warehouse()
    product = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, category, product_name, product_full_name, flavor, price, description, quantity, image_path "
                "FROM products WHERE id = ?",
                (product_id,)
            )
            product = cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Ошибка при запросе товара по ID: {e}")
        finally:
            close_connection_warehouse(conn)
    return product


def get_product_count(category, product_name):
    """Получает количество товара по его product_full_name"""
    conn = create_connection_warehouse()
    product_count = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT quantity FROM products WHERE category = ? AND product_name = ?",
                (category, product_name,)
            )
            result = cursor.fetchone()
            if result:
                product_count = result[0]
        except sqlite3.Error as e:
            print(f"Ошибка при запросе количества товара: {e}")
        finally:
            close_connection_warehouse(conn)
    return product_count


def get_product_id_by_full_name(product_full_name):
    """Получает ID товара по его полному названию (product_full_name)."""
    conn = create_connection_warehouse()
    product_id = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM products WHERE product_full_name = ?",
                (product_full_name,)
            )
            result = cursor.fetchone()
            if result:
                product_id = result[0]
        except sqlite3.Error as e:
            print(f"Ошибка при поиске товара по полному названию: {e}")
        finally:
            close_connection_warehouse(conn)
    return product_id


def update_product_quantity(product_id, new_quantity):
    """Обновляет количество товара на складе."""
    conn = create_connection_warehouse()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE products SET quantity = ? WHERE id = ?",
                (new_quantity, product_id)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении количества товара: {e}")
            return False
        finally:
            close_connection_warehouse(conn)
    return False


def get_product_stock_quantity(product_id):
    """Получает доступное количество товара на складе"""
    import sqlite3
    conn = sqlite3.connect('warehouse.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT quantity FROM products WHERE id = ?",
            (product_id,)
        )
        result = cursor.fetchone()

        if result:
            return result[0]
        return 0

    except sqlite3.Error as e:
        print(f"Ошибка при получении количества товара: {e}")
        return 0

    finally:
        conn.close()


def get_product_quantity(product_id):
    """Получает текущее количество товара по его ID."""
    conn = create_connection_warehouse()
    quantity = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT quantity FROM products WHERE id = ?",
                (product_id,)
            )
            result = cursor.fetchone()
            if result:
                quantity = result[0]
        except sqlite3.Error as e:
            print(f"Ошибка при получении количества товара: {e}")
        finally:
            close_connection_warehouse(conn)
    return quantity


def get_total_value_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(quantity * price) FROM products")
    total_value = cursor.fetchone()[0]
    conn.close()
    return total_value


def get_available_product_names(conn, category_name):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT product_name 
        FROM products 
        WHERE category = ? AND quantity > 0
        """,
        (category_name,)
    )
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def get_products_by_category_and_name(conn, category_name, product_name):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT product_full_name, flavor, price, id, description, quantity, image_path 
        FROM products 
        WHERE category = ? AND product_name = ? AND quantity > 0
        """,
        (category_name, product_name)
    )
    return cursor.fetchall()


def get_product_by_details(category: str, product_name: str, flavor: str) -> Optional[Tuple]:
    """Получает товар по категории, названию и вкусу"""
    conn = create_connection_warehouse()
    product = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id, category, product_name, product_full_name, flavor, 
                   price, description, quantity, image_path, is_active 
                   FROM products 
                   WHERE category = ? AND product_name = ? AND flavor = ? AND is_active = 1""",
                (category, product_name, flavor)
            )
            product = cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Ошибка при поиске товара: {e}")
        finally:
            close_connection_warehouse(conn)
    return product
