import sqlite3
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PreorderDatabase:
    def __init__(self, db_path: str = "preorders.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Инициализация таблиц базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Таблица товаров для предзаказа
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preorder_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    flavor TEXT NOT NULL,
                    description TEXT,
                    price REAL,
                    expected_date DATE,
                    image_path TEXT,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    UNIQUE(category, product_name, flavor)
                )
            ''')

            # Таблица предзаказов пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preorders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (product_id) REFERENCES preorder_products(id),
                    UNIQUE(user_id, product_id)
                )
            ''')

            # Таблица для отслеживания уникальных просмотров
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS product_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, product_id)
                )
            ''')

            # Таблица категорий для работы с ID
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preorder_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')

            # Заполняем таблицу категорий существующими категориями
            cursor.execute('''
                INSERT OR IGNORE INTO preorder_categories (name)
                SELECT DISTINCT category FROM preorder_products WHERE is_active = 1
            ''')

            # Таблица для хранения причин отказов от предзаказов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preorder_cancellations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    custom_reason TEXT,
                    cancelled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    def add_preorder_product(self, category: str, product_name: str, flavor: str,
                             description: Optional[str] = None, price: Optional[float] = None,
                             expected_date: Optional[str] = None,
                             image_path: Optional[str] = None) -> Optional[int]:
        """Добавить товар для предзаказа"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO preorder_products 
                    (category, product_name, flavor, description, price, expected_date, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (category, product_name, flavor, description, price, expected_date, image_path))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении товара для предзаказа: {e}")
            return None

    def get_categories(self) -> List[str]:
        """Получить список категорий товаров для предзаказа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT category FROM preorder_products 
                WHERE is_active = 1
                ORDER BY category
            ''')
            return [row[0] for row in cursor.fetchall()]

    def get_all_categories(self) -> List[str]:
        """Получить все категории (для админа)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT category FROM preorder_products 
                ORDER BY category
            ''')
            return [row[0] for row in cursor.fetchall()]

    def get_all_product_names(self) -> List[str]:
        """Получить все названия товаров (для админа)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT product_name FROM preorder_products 
                ORDER BY product_name
            ''')
            return [row[0] for row in cursor.fetchall()]

    def get_products_by_category(self, category: str) -> List[str]:
        """Получить список товаров в категории"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT product_name FROM preorder_products 
                WHERE category = ? AND is_active = 1
                ORDER BY product_name
            ''', (category,))
            return [row[0] for row in cursor.fetchall()]

    def get_flavors_by_product(self, category: str, product_name: str) -> List[str]:
        """Получить список вкусов товара"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT flavor FROM preorder_products 
                WHERE category = ? AND product_name = ? AND is_active = 1
                ORDER BY flavor
            ''', (category, product_name))
            return [row[0] for row in cursor.fetchall()]

    def get_product_details(self, category: str, product_name: str, flavor: str) -> Optional[Dict[str, Any]]:
        """Получить детали товара"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM preorder_products 
                WHERE category = ? AND product_name = ? AND flavor = ? AND is_active = 1
            ''', (category, product_name, flavor))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def increment_views(self, product_id: int, user_id: int) -> bool:
        """Увеличить счетчик просмотров товара (только уникальные)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Пытаемся вставить запись о просмотре
                cursor.execute('''
                    INSERT OR IGNORE INTO product_views (user_id, product_id)
                    VALUES (?, ?)
                ''', (user_id, product_id))

                # Если вставка прошла успешно (новый просмотр)
                if cursor.rowcount > 0:
                    cursor.execute('''
                        UPDATE preorder_products 
                        SET views = views + 1 
                        WHERE id = ?
                    ''', (product_id,))
                    conn.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при увеличении счетчика просмотров: {e}")
            return False

    def add_preorder(self, user_id: int, product_id: int, quantity: int = 1) -> bool:
        """Добавить предзаказ пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_preorders (user_id, product_id, quantity)
                    VALUES (?, ?, ?)
                ''', (user_id, product_id, quantity))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Предзаказ уже существует
            return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении предзаказа: {e}")
            return False

    def cancel_preorder(self, user_id: int, product_id: int) -> bool:
        """Отменить предзаказ пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_preorders 
                    WHERE user_id = ? AND product_id = ?
                ''', (user_id, product_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отмене предзаказа: {e}")
            return False

    def has_preorder(self, user_id: int, product_id: int) -> bool:
        """Проверить, есть ли у пользователя предзаказ на товар"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM user_preorders 
                WHERE user_id = ? AND product_id = ? AND status = 'active'
            ''', (user_id, product_id))
            return cursor.fetchone()[0] > 0

    def get_user_preorders(self, user_id: int, page: int = 1, per_page: int = 6) -> Dict[str, Any]:
        """Получить предзаказы пользователя с пагинацией"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Получаем общее количество предзаказов
            cursor.execute('''
                SELECT COUNT(*) FROM user_preorders up
                JOIN preorder_products p ON up.product_id = p.id
                WHERE up.user_id = ? AND up.status = 'active' AND p.is_active = 1
            ''', (user_id,))
            total = cursor.fetchone()[0]

            # Получаем предзаказы для текущей страницы
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT p.*, up.quantity, up.created_at as preorder_date
                FROM user_preorders up
                JOIN preorder_products p ON up.product_id = p.id
                WHERE up.user_id = ? AND up.status = 'active' AND p.is_active = 1
                ORDER BY up.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, per_page, offset))

            items = [dict(row) for row in cursor.fetchall()]
            total_pages = (total + per_page - 1) // per_page

            return {
                'items': items,
                'page': page,
                'total_pages': total_pages,
                'total': total
            }

    def get_all_preorder_products(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Получить все товары для предзаказа с пагинацией (для админа)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Получаем общее количество товаров
            cursor.execute('''
                SELECT COUNT(*) FROM preorder_products WHERE is_active = 1
            ''')
            total = cursor.fetchone()[0]

            # Получаем товары для текущей страницы
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT p.*, 
                       COUNT(DISTINCT up.user_id) as preorder_count
                FROM preorder_products p
                LEFT JOIN user_preorders up ON p.id = up.product_id AND up.status = 'active'
                WHERE p.is_active = 1
                GROUP BY p.id
                ORDER BY p.category, p.product_name, p.flavor
                LIMIT ? OFFSET ?
            ''', (per_page, offset))

            items = [dict(row) for row in cursor.fetchall()]
            total_pages = (total + per_page - 1) // per_page

            return {
                'items': items,
                'page': page,
                'total_pages': total_pages,
                'total': total
            }

    def delete_preorder_product(self, product_id: int) -> bool:
        """Удалить товар из предзаказов (деактивировать)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE preorder_products 
                    SET is_active = 0 
                    WHERE id = ?
                ''', (product_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении товара из предзаказов: {e}")
            return False

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Получить товар по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM preorder_products 
                WHERE id = ? AND is_active = 1
            ''', (product_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_category_id(self, category: str) -> Optional[int]:
        """Получить или создать ID категории"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Создаем таблицу категорий если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preorder_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')

            # Пытаемся получить существующую категорию
            cursor.execute('SELECT id FROM preorder_categories WHERE name = ?', (category,))
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                # Создаем новую категорию
                cursor.execute('INSERT INTO preorder_categories (name) VALUES (?)', (category,))
                conn.commit()
                return cursor.lastrowid

    def get_category_by_id(self, category_id: int) -> Optional[str]:
        """Получить название категории по ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM preorder_categories WHERE id = ?', (category_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_categories_with_ids(self) -> List[Dict[str, Any]]:
        """Получить список категорий с их ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Сначала убеждаемся, что все категории есть в таблице категорий
            cursor.execute('''
                INSERT OR IGNORE INTO preorder_categories (name)
                SELECT DISTINCT category FROM preorder_products WHERE is_active = 1
            ''')
            conn.commit()

            # Теперь получаем категории с ID
            cursor.execute('''
                SELECT DISTINCT pc.id, pc.name 
                FROM preorder_categories pc
                JOIN preorder_products pp ON pc.name = pp.category
                WHERE pp.is_active = 1
                ORDER BY pc.name
            ''')
            return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

    def get_products_ids_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """Получить товары с ID по категории"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Получаем название категории
            cursor.execute('SELECT name FROM preorder_categories WHERE id = ?', (category_id,))
            category_result = cursor.fetchone()
            if not category_result:
                return []

            category_name = category_result[0]

            # Получаем уникальные товары с минимальным ID для каждого
            cursor.execute('''
                SELECT MIN(id) as id, product_name 
                FROM preorder_products 
                WHERE category = ? AND is_active = 1
                GROUP BY product_name
                ORDER BY product_name
            ''', (category_name,))
            return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

    def get_flavors_ids_by_product(self, category_id: int, product_id: int) -> List[Dict[str, Any]]:
        """Получить вкусы с ID для товара"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Получаем информацию о товаре
            cursor.execute('SELECT category, product_name FROM preorder_products WHERE id = ?', (product_id,))
            product_info = cursor.fetchone()
            if not product_info:
                return []

            category, product_name = product_info

            # Получаем все вкусы для этого товара
            cursor.execute('''
                SELECT id, flavor 
                FROM preorder_products 
                WHERE category = ? AND product_name = ? AND is_active = 1
                ORDER BY flavor
            ''', (category, product_name))
            return [{'id': row[0], 'flavor': row[1]} for row in cursor.fetchall()]

    def get_users_with_preorder(self, product_id: int) -> List[int]:
        """Получить список пользователей с предзаказом на товар"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT user_id 
                FROM user_preorders 
                WHERE product_id = ? AND status = 'active'
            ''', (product_id,))
            return [row[0] for row in cursor.fetchall()]

    def save_cancellation_reason(self, user_id: int, product_id: int, reason: str, custom_reason: str = None) -> bool:
        """Сохранить причину отказа от предзаказа"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO preorder_cancellations (user_id, product_id, reason, custom_reason)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, product_id, reason, custom_reason))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении причины отказа: {e}")
            return False

    def get_product_preorders_count(self, product_id: int) -> int:
        """Получить количество активных предзаказов на товар"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM user_preorders 
                WHERE product_id = ? AND status = 'active'
            ''', (product_id,))
            return cursor.fetchone()[0]

    def get_cancellation_stats(self) -> Dict[str, Any]:
        """Получить статистику отказов от предзаказов"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Общее количество отказов
            cursor.execute('SELECT COUNT(*) FROM preorder_cancellations')
            total_cancellations = cursor.fetchone()[0]

            # Статистика по причинам
            cursor.execute('''
                SELECT reason, COUNT(*) as count 
                FROM preorder_cancellations 
                GROUP BY reason 
                ORDER BY count DESC
            ''')
            reasons_stats = cursor.fetchall()

            # Последние отказы с пользовательскими причинами
            cursor.execute('''
                SELECT pc.*, pp.product_name, pp.flavor 
                FROM preorder_cancellations pc
                JOIN preorder_products pp ON pc.product_id = pp.id
                WHERE pc.custom_reason IS NOT NULL
                ORDER BY pc.cancelled_at DESC
                LIMIT 10
            ''')
            recent_custom_reasons = cursor.fetchall()

            return {
                'total': total_cancellations,
                'by_reason': reasons_stats,
                'recent_custom': recent_custom_reasons
            }


preorder_db = PreorderDatabase()
