import sqlite3
import json
from typing import List, Tuple, Optional, Dict, Any

DATABASE_NAME = 'shop_bot.db'


def ensure_broadcast_tables():
    """Создает таблицы для рассылок, если они не существуют."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Таблица для шаблонов рассылки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                buttons TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица для истории рассылок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                media_type TEXT,
                media_file TEXT,
                buttons TEXT,
                target_type TEXT NOT NULL,
                target_params TEXT,
                sent_count INTEGER DEFAULT 0,
                total_recipients INTEGER,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        """)

        conn.commit()

    except sqlite3.Error as e:
        print(f"Ошибка при создании таблиц для рассылок: {e}")

    finally:
        conn.close()


def save_broadcast_template(name: str, content: Dict[str, Any]) -> int:
    """Сохраняет шаблон рассылки в базу данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        content_json = json.dumps(content)
        cursor.execute(
            """
            INSERT INTO broadcast_templates (name, content, type, buttons)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                content['text'],
                content.get('type', 'text'),
                json.dumps(content.get('buttons', []))
            )
        )
        conn.commit()
        return cursor.lastrowid

    except sqlite3.Error as e:
        print(f"Ошибка при сохранении шаблона рассылки: {e}")
        return -1

    finally:
        conn.close()


def get_broadcast_templates() -> List[Tuple]:
    """Получает список шаблонов рассылок."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, name, content, type, buttons, created_at
            FROM broadcast_templates
            ORDER BY created_at DESC
            """
        )
        templates = cursor.fetchall()
        return templates

    except sqlite3.Error as e:
        print(f"Ошибка при получении шаблонов рассылок: {e}")
        return []

    finally:
        conn.close()


def get_broadcast_template(template_id: int) -> Optional[Tuple]:
    """Получает шаблон рассылки по ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, name, content, type, buttons, created_at
            FROM broadcast_templates
            WHERE id = ?
            """,
            (template_id,)
        )
        template = cursor.fetchone()
        return template

    except sqlite3.Error as e:
        print(f"Ошибка при получении шаблона рассылки: {e}")
        return None

    finally:
        conn.close()


def start_broadcast(broadcast_data: Dict[str, Any]) -> int:
    """Создает новую запись о рассылке."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO broadcast_history (
                message_text, media_type, media_file, buttons,
                target_type, target_params, total_recipients, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                broadcast_data.get('text', ''),
                broadcast_data.get('media_type', None),
                broadcast_data.get('media_file', None),
                json.dumps(broadcast_data.get('buttons', [])),
                broadcast_data.get('target_type', 'all'),
                json.dumps(broadcast_data.get('target_params', {})),
                broadcast_data.get('total_recipients', 0),
                'pending'
            )
        )
        conn.commit()
        return cursor.lastrowid

    except sqlite3.Error as e:
        print(f"Ошибка при создании рассылки: {e}")
        return -1

    finally:
        conn.close()


def update_broadcast_status(broadcast_id: int, status: str, sent_count: int = None) -> bool:
    """Обновляет статус рассылки."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        if status == 'completed':
            if sent_count is not None:
                cursor.execute(
                    """
                    UPDATE broadcast_history
                    SET status = ?, sent_count = ?, sent_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (status, sent_count, broadcast_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE broadcast_history
                    SET status = ?, sent_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (status, broadcast_id)
                )
        else:
            if sent_count is not None:
                cursor.execute(
                    """
                    UPDATE broadcast_history
                    SET status = ?, sent_count = ?
                    WHERE id = ?
                    """,
                    (status, sent_count, broadcast_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE broadcast_history
                    SET status = ?
                    WHERE id = ?
                    """,
                    (status, broadcast_id)
                )

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при обновлении статуса рассылки: {e}")
        return False

    finally:
        conn.close()


def get_broadcast_history(limit: int = 10) -> List[Tuple]:
    """Получает историю рассылок."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, message_text, target_type, sent_count, total_recipients, status, created_at, sent_at
            FROM broadcast_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        history = cursor.fetchall()
        return history

    except sqlite3.Error as e:
        print(f"Ошибка при получении истории рассылок: {e}")
        return []

    finally:
        conn.close()


def get_broadcast_details(broadcast_id: int) -> Optional[Tuple]:
    """Получает детальную информацию о рассылке."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                id, message_text, media_type, media_file, buttons,
                target_type, target_params, sent_count, total_recipients,
                status, created_at, sent_at
            FROM broadcast_history
            WHERE id = ?
            """,
            (broadcast_id,)
        )
        broadcast = cursor.fetchone()
        return broadcast

    except sqlite3.Error as e:
        print(f"Ошибка при получении информации о рассылке: {e}")
        return None

    finally:
        conn.close()