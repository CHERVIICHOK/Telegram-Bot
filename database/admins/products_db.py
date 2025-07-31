import sqlite3
from typing import List, Tuple, Optional, Dict, Any
from config import DATABASE_NAME


def ensure_product_status_column():
    """Добавляет столбец is_active в таблицу products, если его нет."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(products)")
        columns = [info[1] for info in cursor.fetchall()]

        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1")
            conn.commit()
            print("Столбец is_active успешно добавлен в таблицу products")

    except sqlite3.Error as e:
        print(f"Ошибка при проверке/добавлении столбца is_active: {e}")

    finally:
        conn.close()


def get_paginated_products(category: Optional[str] = None, page: int = 1, per_page: int = 5) -> Tuple[List[Tuple], int]:
    """
    Получает список товаров с пагинацией, опционально фильтруя по категории.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    offset = (page - 1) * per_page

    try:
        # Запрос для получения общего количества товаров
        count_query = "SELECT COUNT(*) FROM products"
        count_params = ()

        if category:
            count_query += " WHERE category = ?"
            count_params = (category,)

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        total_pages = (total_count + per_page - 1) // per_page

        # Запрос для получения товаров с пагинацией
        query = """
            SELECT id, category, product_name, product_full_name, flavor, 
                   price, description, quantity, image_path, is_active 
            FROM products
        """
        params = []

        if category:
            query += " WHERE category = ?"
            params = [category]

        query += " ORDER BY category, product_name, flavor LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        cursor.execute(query, params)
        products = cursor.fetchall()

        return products, total_pages

    except sqlite3.Error as e:
        print(f"Ошибка при получении списка товаров: {e}")
        return [], 0

    finally:
        conn.close()


def add_product(product_data: Dict[str, Any]) -> int:
    """Добавляет новый товар в базу данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO products (
                category, product_name, product_full_name, flavor, 
                price, description, quantity, image_path, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_data.get('category', ''),
                product_data.get('product_name', ''),
                product_data.get('product_full_name', ''),
                product_data.get('flavor', ''),
                product_data.get('price', 0),
                product_data.get('description', ''),
                product_data.get('quantity', 0),
                product_data.get('image_path', ''),
                product_data.get('is_active', 1)
            )
        )
        conn.commit()
        product_id = cursor.lastrowid

        # Проверяем предзаказы при добавлении товара
        if product_data.get('quantity', 0) > 0:
            from utils.preorder_processor import preorder_processor
            if preorder_processor:
                import asyncio
                asyncio.create_task(
                    preorder_processor.check_and_process_preorders(
                        product_data.get('category', ''),
                        product_data.get('product_name', ''),
                        product_data.get('flavor', ''),
                        product_id
                    )
                )

        return product_id

    except sqlite3.Error as e:
        print(f"Ошибка при добавлении товара: {e}")
        return -1

    finally:
        conn.close()


def update_product(product_id: int, update_data: Dict[str, Any]) -> bool:
    """Обновляет информацию о товаре."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Получаем текущую информацию о товаре
        cursor.execute(
            "SELECT category, product_name, flavor, quantity FROM products WHERE id = ?",
            (product_id,)
        )
        current_product = cursor.fetchone()
        old_quantity = current_product[3] if current_product else 0

        update_fields = []
        params = []

        for key, value in update_data.items():
            if key in ['category', 'product_name', 'product_full_name', 'flavor',
                       'price', 'description', 'quantity', 'image_path', 'is_active']:
                update_fields.append(f"{key} = ?")
                params.append(value)

        if not update_fields:
            return False

        query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
        params.append(product_id)

        cursor.execute(query, params)
        conn.commit()

        if current_product and old_quantity == 0 and update_data.get('quantity', 0) > 0:
            from utils.preorder_processor import preorder_processor
            if preorder_processor:
                import asyncio
                asyncio.create_task(
                    preorder_processor.check_and_process_preorders(
                        current_product[0],  # category
                        current_product[1],  # product_name
                        current_product[2],  # flavor
                        product_id
                    )
                )

        return cursor.rowcount > 0

    except sqlite3.Error as e:
        print(f"Ошибка при обновлении товара: {e}")
        return False

    finally:
        conn.close()


def toggle_product_status(product_id: int, is_active: bool) -> bool:
    """Активирует или деактивирует товар."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE products SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, product_id)
        )
        conn.commit()

        return cursor.rowcount > 0

    except sqlite3.Error as e:
        print(f"Ошибка при изменении статуса товара: {e}")
        return False

    finally:
        conn.close()


def get_product_details(product_id: int) -> Optional[Tuple]:
    """Получает полную информацию о товаре по его ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, category, product_name, product_full_name, flavor, 
                   price, description, quantity, image_path, is_active
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        )
        product = cursor.fetchone()
        return product

    except sqlite3.Error as e:
        print(f"Ошибка при получении информации о товаре: {e}")
        return None

    finally:
        conn.close()


def get_categories() -> List[str]:
    """Получает список всех категорий товаров."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cursor.fetchall()]
        return categories

    except sqlite3.Error as e:
        print(f"Ошибка при получении категорий: {e}")
        return []

    finally:
        conn.close()


def add_category(category_name: str) -> bool:
    """Добавляет новую категорию (создает фиктивный товар)."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли категория
        cursor.execute("SELECT COUNT(*) FROM products WHERE category = ?", (category_name,))
        if cursor.fetchone()[0] > 0:
            return False

        # Добавляем фиктивный товар с новой категорией
        cursor.execute(
            """
            INSERT INTO products (
                category, product_name, product_full_name, flavor, 
                price, description, quantity, image_path, is_active
            ) VALUES (?, 'Новый товар', 'Новый товар', '', 0, '', 0, '', 0)
            """,
            (category_name,)
        )
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при добавлении категории: {e}")
        return False

    finally:
        conn.close()


def update_category(old_name: str, new_name: str) -> bool:
    """Обновляет название категории для всех товаров."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE products SET category = ? WHERE category = ?",
            (new_name, old_name)
        )
        conn.commit()
        return cursor.rowcount > 0

    except sqlite3.Error as e:
        print(f"Ошибка при обновлении категории: {e}")
        return False

    finally:
        conn.close()


def delete_category(category_name: str) -> bool:
    """Удаляет категорию (деактивирует все товары в этой категории)."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE products SET is_active = 0 WHERE category = ?",
            (category_name,)
        )
        conn.commit()
        return cursor.rowcount > 0

    except sqlite3.Error as e:
        print(f"Ошибка при удалении категории: {e}")
        return False

    finally:
        conn.close()