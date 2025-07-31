import logging
import sqlite3
from typing import List, Tuple, Dict
from datetime import datetime, timedelta

DATABASE_NAME = 'shop_bot.db'

logger = logging.getLogger(__name__)


def get_all_users() -> List[Tuple]:
    """Получает список всех пользователей из базы данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT telegram_id, username, first_name, last_name, first_login_date FROM users"
        )
        users = cursor.fetchall()
        return users

    except sqlite3.Error as e:
        print(f"Ошибка при получении списка пользователей: {e}")
        return []

    finally:
        conn.close()


def get_active_users(days: int = 30) -> List[int]:
    """Получает ID пользователей, делавших заказы за последние N дней."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """
            SELECT DISTINCT user_id FROM orders 
            WHERE order_date >= ?
            """,
            (cutoff_date,)
        )

        users = [row[0] for row in cursor.fetchall()]
        return users

    except sqlite3.Error as e:
        print(f"Ошибка при получении активных пользователей: {e}")
        return []

    finally:
        conn.close()


def get_user_regions() -> Dict[str, List[int]]:
    """Получает список пользователей по регионам."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT address_region, user_id FROM user_addresses
            GROUP BY user_id
            """
        )

        regions = {}
        for row in cursor.fetchall():
            region, user_id = row
            if region:
                if region not in regions:
                    regions[region] = []
                regions[region].append(user_id)

        return regions

    except sqlite3.Error as e:
        print(f"Ошибка при получении пользователей по регионам: {e}")
        return {}

    finally:
        conn.close()


def count_users() -> int:
    """Получает общее количество пользователей."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count

    except sqlite3.Error as e:
        print(f"Ошибка при подсчете пользователей: {e}")
        return 0

    finally:
        conn.close()


def get_username_by_telegram_id(telegram_id: int) -> str | None:
    """Получает username пользователя по telegram_id из базы данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT username FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        result = cursor.fetchone()
        if result:
            return result[0]  # username
        return None

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении username по telegram_id: {e}")
        return None

    finally:
        conn.close()
