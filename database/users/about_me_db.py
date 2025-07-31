import logging
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

DATABASE_NAME = 'shop_bot.db'

logger = logging.getLogger(__name__)


def create_tables():
    """Создает таблицы для хранения информации о пользователе"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Таблица личных данных
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_personal_info (
                telegram_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                birth_date TEXT,
                gender TEXT,
                email TEXT,
                phone TEXT,
                updated_at TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')

        # Упрощенная таблица адресов доставки (без типов)
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_addresses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER,
                        address TEXT,
                        courier_instructions TEXT,
                        is_default BOOLEAN DEFAULT 0,
                        created_at TEXT,
                        FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                    )
                ''')

        # Если таблица уже существует, добавляем колонку
        cursor.execute("PRAGMA table_info(user_addresses)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'courier_instructions' not in columns:
            cursor.execute('ALTER TABLE user_addresses ADD COLUMN courier_instructions TEXT')

        # Таблица предпочтений доставки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_delivery_preferences (
                telegram_id INTEGER PRIMARY KEY,
                preferred_time_start TEXT,
                preferred_time_end TEXT,
                updated_at TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')

        # Таблица для сбора статистики использования раздела "О себе"
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS about_me_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                action_type TEXT,
                action_details TEXT,
                timestamp TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')

        conn.commit()
        logger.info("Таблицы для раздела 'О себе' успешно созданы")

    except sqlite3.Error as e:
        logger.error(f"Ошибка при создании таблиц: {e}")

    finally:
        conn.close()


def log_user_action(telegram_id: int, action_type: str, action_details: str = None):
    """Логирует действия пользователя в разделе 'О себе'"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO about_me_statistics (telegram_id, action_type, action_details, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, action_type, action_details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()

    except sqlite3.Error as e:
        logger.error(f"Ошибка при логировании действия пользователя: {e}")

    finally:
        conn.close()


def get_user_personal_info(telegram_id: int) -> Optional[Dict]:
    """Получает личные данные пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT first_name, last_name, birth_date, gender, email, phone
            FROM user_personal_info
            WHERE telegram_id = ?
        ''', (telegram_id,))

        result = cursor.fetchone()
        if result:
            return {
                'first_name': result[0],
                'last_name': result[1],
                'birth_date': result[2],
                'gender': result[3],
                'email': result[4],
                'phone': result[5]
            }
        return None

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении личных данных: {e}")
        return None

    finally:
        conn.close()


def update_user_personal_info(telegram_id: int, field: str, value: str) -> bool:
    """Обновляет конкретное поле личных данных пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли запись
        cursor.execute('SELECT telegram_id FROM user_personal_info WHERE telegram_id = ?', (telegram_id,))
        exists = cursor.fetchone()

        if exists:
            # Обновляем существующую запись
            query = f'''
                UPDATE user_personal_info 
                SET {field} = ?, updated_at = ? 
                WHERE telegram_id = ?
            '''
            cursor.execute(query, (value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telegram_id))
        else:
            # Создаем новую запись
            cursor.execute('''
                INSERT INTO user_personal_info (telegram_id, {}, updated_at)
                VALUES (?, ?, ?)
            '''.format(field), (telegram_id, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()

        # Логируем успешное обновление
        log_user_action(telegram_id, f"updated_{field}", value)

        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при обновлении личных данных: {e}")
        return False

    finally:
        conn.close()


def get_user_addresses(telegram_id: int) -> List[Dict]:
    """Получает все адреса пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, address, is_default, courier_instructions
            FROM user_addresses
            WHERE telegram_id = ?
            ORDER BY is_default DESC, created_at DESC
        ''', (telegram_id,))

        addresses = []
        for row in cursor.fetchall():
            addresses.append({
                'id': row[0],
                'address': row[1],
                'is_default': bool(row[2]),
                'courier_instructions': row[3]
            })

        return addresses

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении адресов: {e}")
        return []

    finally:
        conn.close()


def add_user_address(telegram_id: int, address: str, is_default: bool = False) -> bool:
    """Добавляет новый адрес пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Если это адрес по умолчанию, сбрасываем флаг у других адресов
        if is_default:
            cursor.execute('''
                UPDATE user_addresses 
                SET is_default = 0 
                WHERE telegram_id = ?
            ''', (telegram_id,))

        cursor.execute('''
            INSERT INTO user_addresses (telegram_id, address, is_default, created_at)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, address, is_default, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()

        # Логируем добавление адреса
        log_user_action(telegram_id, "added_address", address)

        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении адреса: {e}")
        return False

    finally:
        conn.close()


def update_user_address(address_id: int, telegram_id: int, address: str) -> bool:
    """Обновляет адрес пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE user_addresses 
            SET address = ? 
            WHERE id = ? AND telegram_id = ?
        ''', (address, address_id, telegram_id))

        conn.commit()

        if cursor.rowcount > 0:
            log_user_action(telegram_id, "updated_address", f"id:{address_id}")
            return True
        return False

    except sqlite3.Error as e:
        logger.error(f"Ошибка при обновлении адреса: {e}")
        return False

    finally:
        conn.close()


def delete_user_address(address_id: int, telegram_id: int) -> bool:
    """Удаляет адрес пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM user_addresses 
            WHERE id = ? AND telegram_id = ?
        ''', (address_id, telegram_id))

        conn.commit()

        if cursor.rowcount > 0:
            log_user_action(telegram_id, "deleted_address", f"id:{address_id}")
            return True
        return False

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении адреса: {e}")
        return False

    finally:
        conn.close()


def set_default_address(address_id: int, telegram_id: int) -> bool:
    """Устанавливает адрес по умолчанию"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        # Сбрасываем флаг у всех адресов
        cursor.execute('''
            UPDATE user_addresses 
            SET is_default = 0 
            WHERE telegram_id = ?
        ''', (telegram_id,))

        # Устанавливаем флаг для выбранного адреса
        cursor.execute('''
            UPDATE user_addresses 
            SET is_default = 1 
            WHERE id = ? AND telegram_id = ?
        ''', (address_id, telegram_id))

        conn.commit()

        if cursor.rowcount > 0:
            log_user_action(telegram_id, "set_default_address", f"id:{address_id}")
            return True
        return False

    except sqlite3.Error as e:
        logger.error(f"Ошибка при установке адреса по умолчанию: {e}")
        return False

    finally:
        conn.close()


def get_delivery_preferences(telegram_id: int) -> Optional[Dict]:
    """Получает предпочтения по времени доставки"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT preferred_time_start, preferred_time_end
            FROM user_delivery_preferences
            WHERE telegram_id = ?
        ''', (telegram_id,))

        result = cursor.fetchone()
        if result:
            return {
                'start_time': result[0],
                'end_time': result[1]
            }
        return None

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении предпочтений доставки: {e}")
        return None

    finally:
        conn.close()


def update_delivery_preferences(telegram_id: int, start_time: str, end_time: str) -> bool:
    """Обновляет предпочтения по времени доставки"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO user_delivery_preferences 
            (telegram_id, preferred_time_start, preferred_time_end, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, start_time, end_time, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()

        # Логируем обновление времени
        log_user_action(telegram_id, "updated_delivery_time", f"{start_time}-{end_time}")

        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при обновлении предпочтений доставки: {e}")
        return False

    finally:
        conn.close()


def update_courier_instructions(address_id: int, telegram_id: int, instructions: str) -> bool:
    """Обновляет инструкции для курьера"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE user_addresses 
            SET courier_instructions = ? 
            WHERE id = ? AND telegram_id = ?
        ''', (instructions, address_id, telegram_id))

        conn.commit()

        if cursor.rowcount > 0:
            log_user_action(telegram_id, "updated_courier_instructions", f"id:{address_id}")
            return True
        return False

    except sqlite3.Error as e:
        logger.error(f"Ошибка при обновлении инструкций: {e}")
        return False

    finally:
        conn.close()



# Вызываем создание таблиц при импорте модуля
create_tables()
