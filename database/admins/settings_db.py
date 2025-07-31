import logging
from database.users.database_connection import create_connection as get_db_connection


logger = logging.getLogger(__name__)

DEFAULT_ORDER_PROCESSING_TIMEOUT = 20
DEFAULT_NOTIFICATION_INTERVAL = 10
DEFAULT_NOTIFICATION_TEXT = (
    "⚠️ <b>Внимание! Заказ требует обработки!</b>\n\n"
    "Заказ #{order_id} не был обработан в течение {elapsed_time} минут.\n"
    "Текущий статус: В обработке\n\n"
    "Пожалуйста, обработайте заказ как можно скорее!"
)


def init_settings_table():
    """Инициализирует таблицу настроек, если она не существует"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        default_settings = [
            ('order_processing_timeout', str(DEFAULT_ORDER_PROCESSING_TIMEOUT)),
            ('notification_interval', str(DEFAULT_NOTIFICATION_INTERVAL)),
            ('notification_text', DEFAULT_NOTIFICATION_TEXT)
        ]

        for key, value in default_settings:
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

        conn.commit()
        conn.close()
        logger.info("Settings table initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing settings table: {e}")


def get_setting(key: str, default: str = "") -> str:
    """Получает значение настройки по ключу"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]
        else:
            init_settings_table()
            return default

    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return default


def update_setting(key: str, value: str) -> bool:
    """Обновляет значение настройки"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
            (value, key)
        )

        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

        conn.commit()
        conn.close()

        logger.info(f"Setting {key} updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        return False


def get_order_processing_timeout() -> int:
    """Получает время ожидания обработки заказа в минутах"""
    return int(get_setting('order_processing_timeout', str(DEFAULT_ORDER_PROCESSING_TIMEOUT)))


def update_order_processing_timeout(minutes: int) -> bool:
    """Обновляет время ожидания обработки заказа"""
    return update_setting('order_processing_timeout', str(minutes))


def get_notification_interval() -> int:
    """Получает интервал повторных уведомлений в минутах"""
    return int(get_setting('notification_interval', str(DEFAULT_NOTIFICATION_INTERVAL)))


def update_notification_interval(minutes: int) -> bool:
    """Обновляет интервал повторных уведомлений"""
    return update_setting('notification_interval', str(minutes))


def get_notification_text() -> str:
    """Получает текст уведомления"""
    return get_setting('notification_text', DEFAULT_NOTIFICATION_TEXT)


def update_notification_text(text: str) -> bool:
    """Обновляет текст уведомления"""
    return update_setting('notification_text', text)


init_settings_table()