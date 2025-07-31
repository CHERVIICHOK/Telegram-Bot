import logging
import sqlite3

from config import DB_REVIEWS_PATH

logger = logging.getLogger(__name__)


def connect_db():
    """Устанавливает соединение с базой данных."""
    try:
        conn = sqlite3.connect(DB_REVIEWS_PATH)
        cursor = conn.cursor()
        logger.info(f"Успешно подключено к базе данных: {DB_REVIEWS_PATH}")
        return conn, cursor
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None, None


def close_db(conn):
    """Закрывает соединение с базой данных."""
    if conn:
        conn.close()
        logger.info("Соединение с базой данных закрыто.")


def create_product_reviews_table():
    """Создает таблицу product_reviews, если она не существует."""
    conn, cursor = connect_db()
    if not conn:
        return False
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        conn.commit()
        logger.info("Таблица product_reviews успешно создана (или уже существовала).")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при создании таблицы product_reviews: {e}")
        return False
    finally:
        close_db(conn)


def create_delivery_comments_table():
    """Создает таблицу delivery_comments, если она не существует."""
    conn, cursor = connect_db()
    if not conn:
        return False
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                comment TEXT,
                rating INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """)
        conn.commit()
        logger.info("Таблица delivery_comments успешно создана (или уже существовала).")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при создании таблицы delivery_comments: {e}")
        return False
    finally:
        close_db(conn)


def add_product_review(user_id, product_id, rating, comment):
    """Добавляет отзыв о товаре в базу данных."""
    conn, cursor = connect_db()
    if not conn:
        return False
    try:
        cursor.execute("""
            INSERT INTO product_reviews (user_id, product_id, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, product_id, rating, comment))
        conn.commit()
        logger.info(f"Отзыв от пользователя {user_id} о товаре {product_id} успешно добавлен.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении отзыва: {e}")
        return False
    finally:
        close_db(conn)


def get_product_reviews_by_product(product_id):
    """Возвращает все отзывы о конкретном товаре."""
    conn, cursor = connect_db()
    if not conn:
        return []
    try:
        cursor.execute("""
            SELECT id, user_id, rating, comment, created_at
            FROM product_reviews
            WHERE product_id = ?
        """, (product_id,))
        rows = cursor.fetchall()
        reviews = []
        for row in rows:
            reviews.append({
                'id': row[0],
                'user_id': row[1],
                'rating': row[2],
                'comment': row[3],
                'created_at': row[4]
            })
        return reviews
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении отзывов о товаре: {e}")
        return []
    finally:
        close_db(conn)


def get_average_rating(product_id):
    """Возвращает средний рейтинг товара."""
    conn, cursor = connect_db()
    if not conn:
        return None
    try:
        cursor.execute("""
            SELECT AVG(rating)
            FROM product_reviews
            WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        else:
            return None
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении среднего рейтинга: {e}")
        return None
    finally:
        close_db(conn)


def add_delivery_comment(user_id, order_id, rating, comment):
    """Добавляет комментарий о доставке в базу данных."""
    conn, cursor = connect_db()
    if not conn:
        return False
    try:
        cursor.execute("""
            INSERT INTO delivery_comments (user_id, order_id, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, order_id, rating, comment))
        conn.commit()
        logger.info(f"Комментарий о доставке от пользователя {user_id} для заказа {order_id} успешно добавлен.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении комментария о доставке: {e}")
        return False
    finally:
        close_db(conn)


def get_delivery_comments_by_order_id(order_id):
    """Возвращает все комментарии о доставке для конкретного заказа."""
    conn, cursor = connect_db()
    if not conn:
        return []
    try:
        cursor.execute("""
            SELECT id, user_id, rating, comment, created_at
            FROM delivery_comments
            WHERE order_id = ?
        """, (order_id,))
        rows = cursor.fetchall()
        comments = []
        for row in rows:
            comments.append({
                'id': row[0],
                'user_id': row[1],
                'rating': row[2],
                'comment': row[3],
                'created_at': row[4]
            })
        return comments
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении комментариев о доставке для заказа {order_id}: {e}")
        return []
    finally:
        close_db(conn)


def has_delivery_comment(user_id: int, order_id: int) -> bool:
    """Проверяет, оставил ли пользователь комментарий о доставке для данного заказа."""
    conn, cursor = connect_db()
    if not conn:
        return False
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM delivery_comments
            WHERE user_id = ? AND order_id = ?
        """, (user_id, order_id))
        result = cursor.fetchone()
        if result and result[0] > 0:
            return True
        else:
            return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка при проверке наличия комментария о доставке: {e}")
        return False
    finally:
        close_db(conn)


def has_product_review(user_id: int, product_id: int) -> bool:
    """Проверяет, оставил ли пользователь отзыв о товаре."""
    conn, cursor = connect_db()
    if not conn:
        return False
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM product_reviews
            WHERE user_id = ? AND product_id = ?
        """, (user_id, product_id))
        result = cursor.fetchone()
        if result and result[0] > 0:
            return True
        else:
            return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка при проверке наличия отзыва о товаре: {e}")
        return False
    finally:
        close_db(conn)
