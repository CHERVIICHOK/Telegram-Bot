import logging
import sqlite3

logger = logging.getLogger(__name__)

DATABASE_FILE = "shop_bot.db"  # Имя файла вашей основной базы данных бота


def create_connection():
    """
    Создает соединение с базой данных SQLite.
    Возвращает объект соединения или None в случае ошибки.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        # Включаем поддержку внешних ключей (важно для FOREIGN KEY)
        conn.execute("PRAGMA foreign_keys = ON")
        logging.info(f"Успешное подключение к базе данных SQLite: {DATABASE_FILE}")
    except sqlite3.Error as e:
        logging.error(f"Ошибка подключения к базе данных SQLite '{DATABASE_FILE}': {e}", exc_info=True)
    return conn


def close_connection(conn):
    """
    Закрывает соединение с базой данных.
    """
    if conn:
        conn.close()
        logging.info(f"Соединение с SQLite '{DATABASE_FILE}' закрыто.")


def create_users_table():
    """
    Создает таблицу users, если она не существует.
    """
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY, -- Telegram ID пользователя, уникальный
                    username TEXT,                  -- Имя пользователя в Telegram (может быть None)
                    first_name TEXT,                -- Имя пользователя
                    last_name TEXT,                 -- Фамилия пользователя (может быть None)
                    first_login_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP -- Дата и время первой регистрации
                )
            """)
            conn.commit()
            logging.info("Таблица 'users' успешно создана (или уже существовала).")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы 'users': {e}", exc_info=True)
            conn.rollback()  # Откатываем изменения в случае ошибки
        finally:
            close_connection(conn)


def create_favorites_table():
    """
    Создает таблицу user_favorites для хранения избранных товаров пользователей,
    если она не существует. Также создает индекс для ускорения поиска.
    """
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Создание таблицы user_favorites
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Уникальный ID записи
                    user_id INTEGER NOT NULL,             -- ID пользователя (ссылка на users.telegram_id)
                    product_id INTEGER NOT NULL,          -- ID товара (из warehouse.db, без прямой связи)
                    added_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Дата добавления

                    -- Внешний ключ для связи с таблицей users
                    -- ON DELETE CASCADE означает, что при удалении пользователя из таблицы users,
                    -- все его записи в user_favorites также будут удалены автоматически.
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,

                    -- Ограничение уникальности: один пользователь не может добавить
                    -- один и тот же товар в избранное дважды.
                    UNIQUE (user_id, product_id)
                )
            """)
            logging.info("Таблица 'user_favorites' успешно создана (или уже существовала).")

            # Создание индекса для ускорения выборок по user_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id
                ON user_favorites (user_id)
            """)
            logging.info(
                "Индекс 'idx_user_favorites_user_id' для таблицы 'user_favorites' создан (или уже существовал).")

            conn.commit()  # Применяем изменения (создание таблицы и индекса)
            logging.info("Изменения для 'user_favorites' успешно применены.")

        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы 'user_favorites' или индекса: {e}", exc_info=True)
            conn.rollback()  # Откатываем изменения в случае ошибки
        finally:
            close_connection(conn)
