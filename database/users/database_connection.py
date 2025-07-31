import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

DATABASE_FILE = "shop_bot.db"


def create_connection():
    """
    Создает соединение с базой данных SQLite.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        logging.info(f"Успешное подключение к базе данных SQLite: {DATABASE_FILE}")
    except sqlite3.Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
    return conn


def close_connection(conn):
    """
    Закрывает соединение с базой данных.
    """
    if conn:
        conn.close()
        logging.info("Соединение с базой данных закрыто.")


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
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_login_date TEXT
                )
            """)
            conn.commit()
            logging.info("Таблица 'users' успешно создана (или уже существовала).")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы 'users': {e}")
        finally:
            close_connection(conn)
