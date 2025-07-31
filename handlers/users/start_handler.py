from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from database.users.database_connection import create_connection, close_connection
import sqlite3
import datetime
from keyboards.users.keyboards import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start.
    Проверяет, есть ли пользователь в базе данных, и выводит приветствие с главным меню.
    """
    conn = create_connection()
    user_telegram_id = message.from_user.id
    user_name = message.from_user.first_name if message.from_user.first_name else "пользователь"

    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (user_telegram_id,))
            existing_user = cursor.fetchone()

            if existing_user:
                await message.answer(f"С возвращением, {user_name}! 👋", reply_markup=main_menu_keyboard)
            else:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO users (telegram_id, username, first_name, last_name, first_login_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_telegram_id, message.from_user.username, message.from_user.first_name,
                    message.from_user.last_name,
                    now))
                conn.commit()
                await message.answer(f"Привет, {user_name}! 👋 Добро пожаловать в наш магазин впервые!",
                                     reply_markup=main_menu_keyboard)

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
            await message.answer(
                "Произошла ошибка при обработке команды /start. Попробуйте позже.", reply_markup=main_menu_keyboard)
        finally:
            close_connection(conn)
    else:
        await message.answer("Не удалось подключиться к базе данных. Попробуйте позже.",
                             reply_markup=main_menu_keyboard)
