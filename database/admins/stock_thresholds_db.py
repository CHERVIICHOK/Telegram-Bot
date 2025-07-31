import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple


def create_stock_thresholds_table(conn: sqlite3.Connection) -> None:
    """
    Создает таблицы для системы уведомлений о низком остатке товаров
    """
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_thresholds (
        product_id INTEGER PRIMARY KEY,
        threshold INTEGER NOT NULL,
        last_notification_date TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_notification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        current_stock INTEGER NOT NULL,
        threshold INTEGER NOT NULL,
        notification_time TEXT NOT NULL,
        delivered INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    ''')

    conn.commit()


def set_product_threshold(conn: sqlite3.Connection, product_id: int, threshold: int) -> None:
    """
    Устанавливает порог уведомления для товара
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO stock_thresholds (product_id, threshold) VALUES (?, ?)",
        (product_id, threshold)
    )
    conn.commit()


def get_product_threshold(conn: sqlite3.Connection, product_id: int) -> Optional[int]:
    """
    Получает порог уведомления для товара
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT threshold FROM stock_thresholds WHERE product_id = ?",
        (product_id,)
    )
    result = cursor.fetchone()
    return result[0] if result else None


def get_all_product_thresholds(conn: sqlite3.Connection) -> List[Tuple[int, int]]:
    """
    Получает все установленные пороги уведомлений
    """
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, threshold FROM stock_thresholds")
    return cursor.fetchall()


def update_last_notification_date(conn: sqlite3.Connection, product_id: int) -> None:
    """
    Обновляет дату последнего уведомления для товара
    """
    now = datetime.datetime.now().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE stock_thresholds SET last_notification_date = ? WHERE product_id = ?",
        (now, product_id)
    )
    conn.commit()


def get_last_notification_date(conn: sqlite3.Connection, product_id: int) -> Optional[str]:
    """
    Получает дату последнего уведомления для товара
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_notification_date FROM stock_thresholds WHERE product_id = ?",
        (product_id,)
    )
    result = cursor.fetchone()
    return result[0] if result else None


def log_stock_notification(
        conn: sqlite3.Connection,
        product_id: int,
        product_name: str,
        current_stock: int,
        threshold: int,
        delivered: bool = False
) -> int:
    """
    Добавляет запись в журнал уведомлений
    """
    now = datetime.datetime.now().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO stock_notification_log 
        (product_id, product_name, current_stock, threshold, notification_time, delivered)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (product_id, product_name, current_stock, threshold, now, 1 if delivered else 0)
    )
    conn.commit()
    return cursor.lastrowid


def update_notification_delivered(conn: sqlite3.Connection, notification_id: int, delivered: bool = True) -> None:
    """
    Обновляет статус доставки уведомления
    """
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE stock_notification_log SET delivered = ? WHERE id = ?",
        (1 if delivered else 0, notification_id)
    )
    conn.commit()


def get_recent_notifications(
        conn: sqlite3.Connection,
        product_id: Optional[int] = None,
        limit: int = 10,
        offset: int = 0
) -> List[Dict]:
    """
    Получает последние уведомления из журнала
    """
    cursor = conn.cursor()

    if product_id:
        cursor.execute(
            """
            SELECT * FROM stock_notification_log 
            WHERE product_id = ? 
            ORDER BY notification_time DESC 
            LIMIT ? OFFSET ?
            """,
            (product_id, limit, offset)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM stock_notification_log 
            ORDER BY notification_time DESC 
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )

    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
