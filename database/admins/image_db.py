# database/admins/image_db.py
import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def create_product_images_table():
    """Создает таблицу product_images если она не существует"""
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS product_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                image_absolute_path TEXT NOT NULL,
                category TEXT,
                upload_date TEXT,
                last_modified TEXT,
                is_active BOOLEAN DEFAULT 1,
                file_size INTEGER,
                content_type TEXT
            )
        ''')
        conn.commit()
        logger.info("Таблица product_images создана или уже существует")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы product_images: {e}")
        return False
    finally:
        conn.close()


def get_db_connection():
    """Создает соединение с базой данных warehouse.db"""
    conn = sqlite3.connect('warehouse.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_product_image_by_name(product_name):
    """Получает информацию об изображении по названию продукта"""
    conn = get_db_connection()
    try:
        image = conn.execute(
            'SELECT * FROM product_images WHERE product_name = ?',
            (product_name,)
        ).fetchone()
        return dict(image) if image else None
    except Exception as e:
        logger.error(f"Ошибка при получении изображения: {e}")
        return None
    finally:
        conn.close()


def add_or_update_product_image(product_name, image_path, category, file_size, content_type):
    """Добавляет или обновляет запись об изображении продукта"""
    conn = get_db_connection()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Проверяем существует ли уже запись для данного продукта
        existing_image = conn.execute(
            'SELECT id FROM product_images WHERE product_name = ?',
            (product_name,)
        ).fetchone()

        if existing_image:
            # Обновляем существующую запись
            conn.execute('''
                UPDATE product_images 
                SET image_absolute_path = ?, last_modified = ?, 
                    file_size = ?, content_type = ?, is_active = ?
                WHERE product_name = ?
            ''', (image_path, current_time, file_size, content_type, True, product_name))
        else:
            # Создаем новую запись
            conn.execute('''
                INSERT INTO product_images 
                (product_name, image_absolute_path, category, upload_date, 
                 last_modified, is_active, file_size, content_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_name, image_path, category, current_time,
                  current_time, True, file_size, content_type))

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении/обновлении изображения: {e}")
        return False
    finally:
        conn.close()


def get_categories():
    """Получает список всех категорий продуктов"""
    conn = get_db_connection()
    try:
        categories = conn.execute(
            'SELECT DISTINCT category FROM products WHERE is_active = 1'
        ).fetchall()
        return [category['category'] for category in categories]
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        return []
    finally:
        conn.close()


def get_product_names_by_category(category):
    """Получает список названий продуктов по категории"""
    conn = get_db_connection()
    try:
        products = conn.execute(
            'SELECT DISTINCT product_name FROM products WHERE category = ? AND is_active = 1',
            (category,)
        ).fetchall()
        return [product['product_name'] for product in products]
    except Exception as e:
        logger.error(f"Ошибка при получении продуктов: {e}")
        return []
    finally:
        conn.close()
