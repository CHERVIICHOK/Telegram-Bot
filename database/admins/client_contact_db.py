import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Создает подключение к базе данных"""
    return sqlite3.connect('shop_bot.db')


def init_client_messages_table():
    """Инициализирует таблицу для логирования сообщений клиентам"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_messages_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    client_id INTEGER NOT NULL,
                    message_text TEXT,
                    message_type TEXT NOT NULL,
                    image_file_id TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            ''')
            conn.commit()
            logger.info("Таблица client_messages_log инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы client_messages_log: {e}")


def log_message_sent(
        admin_id: int,
        client_id: int,
        message_text: Optional[str],
        message_type: str,
        image_file_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
) -> bool:
    """
    Логирует отправленное сообщение в базу данных

    Args:
        admin_id: ID администратора
        client_id: ID клиента
        message_text: Текст сообщения
        message_type: Тип сообщения (text/image)
        image_file_id: ID файла изображения в Telegram
        success: Успешность отправки
        error_message: Сообщение об ошибке

    Returns:
        bool: Успешность записи в БД
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO client_messages_log 
                (admin_id, client_id, message_text, message_type, image_file_id, success, error_message, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                admin_id,
                client_id,
                message_text,
                message_type,
                image_file_id,
                success,
                error_message,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка при логировании сообщения: {e}")
        return False


def get_recent_messages(client_id: int, limit: int = 10) -> List[Dict]:
    """
    Получает историю последних сообщений клиенту

    Args:
        client_id: ID клиента
        limit: Количество сообщений

    Returns:
        Список словарей с информацией о сообщениях
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    admin_id,
                    message_text,
                    message_type,
                    sent_at,
                    success,
                    error_message
                FROM client_messages_log
                WHERE client_id = ?
                ORDER BY sent_at DESC
                LIMIT ?
            ''', (client_id, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении истории сообщений: {e}")
        return []


def get_client_info(client_id: int) -> Optional[Dict]:
    """
    Получает информацию о клиенте по его Telegram ID

    Args:
        client_id: Telegram ID клиента

    Returns:
        Словарь с информацией о клиенте или None
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    first_login_date
                FROM users
                WHERE telegram_id = ?
            ''', (client_id,))

            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении информации о клиенте: {e}")
        return None


def get_client_orders(client_id: int, limit: int = 5) -> List[Dict]:
    """
    Получает последние заказы клиента

    Args:
        client_id: Telegram ID клиента
        limit: Количество заказов

    Returns:
        Список словарей с информацией о заказах
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    id,
                    user_order_id,
                    status,
                    created_at,
                    delivery_date,
                    delivery_type,
                    payment_method
                FROM orders
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (client_id, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении заказов клиента: {e}")
        return []


def search_clients_by_name(search_query: str) -> List[Dict]:
    """
    Поиск клиентов по имени или username

    Args:
        search_query: Поисковый запрос

    Returns:
        Список найденных клиентов
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            search_pattern = f'%{search_query}%'
            cursor.execute('''
                SELECT 
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    first_login_date
                FROM users
                WHERE username LIKE ? 
                   OR first_name LIKE ? 
                   OR last_name LIKE ?
                LIMIT 20
            ''', (search_pattern, search_pattern, search_pattern))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при поиске клиентов: {e}")
        return []


def get_message_statistics(admin_id: Optional[int] = None) -> Dict:
    """
    Получает статистику отправленных сообщений

    Args:
        admin_id: ID администратора (если None - общая статистика)

    Returns:
        Словарь со статистикой
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            base_query = '''
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_messages,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_messages,
                    COUNT(DISTINCT client_id) as unique_clients
                FROM client_messages_log
            '''

            if admin_id:
                cursor.execute(base_query + ' WHERE admin_id = ?', (admin_id,))
            else:
                cursor.execute(base_query)

            result = cursor.fetchone()

            return {
                'total_messages': result[0] or 0,
                'successful_messages': result[1] or 0,
                'failed_messages': result[2] or 0,
                'unique_clients': result[3] or 0
            }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return {
            'total_messages': 0,
            'successful_messages': 0,
            'failed_messages': 0,
            'unique_clients': 0
        }


# Инициализация таблицы при импорте модуля
init_client_messages_table()