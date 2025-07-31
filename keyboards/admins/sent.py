import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.enums import ParseMode


async def send_message_to_user(bot_token: str, user_id: int, message: str):
    """
    Отправляет сообщение пользователю через Telegram бота

    Args:
        bot_token: Токен вашего бота
        user_id: Telegram ID пользователя
        message: Текст сообщения
    """
    # Создаем экземпляр бота
    bot = Bot(token=bot_token)

    try:
        # Отправляем сообщение
        sent_message = await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.HTML  # Можно использовать ParseMode.MARKDOWN_V2
        )

        print(f"✅ Сообщение успешно отправлено!")
        print(f"Message ID: {sent_message.message_id}")
        print(f"Date: {sent_message.date}")

        return sent_message

    except TelegramForbiddenError:
        print("❌ Ошибка: Бот заблокирован пользователем")
    except TelegramBadRequest as e:
        print(f"❌ Ошибка запроса: {e.message}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
    finally:
        # Закрываем сессию бота
        await bot.session.close()


async def send_multiple_messages(bot_token: str, messages_data: list):
    """
    Отправляет сообщения нескольким пользователям

    Args:
        bot_token: Токен бота
        messages_data: Список словарей с user_id и text
    """
    bot = Bot(token=bot_token)

    results = []
    for data in messages_data:
        try:
            msg = await bot.send_message(
                chat_id=data['user_id'],
                text=data['text'],
                parse_mode=ParseMode.HTML
            )
            results.append({
                'user_id': data['user_id'],
                'success': True,
                'message_id': msg.message_id
            })
            print(f"✅ Отправлено пользователю {data['user_id']}")

        except TelegramForbiddenError:
            results.append({
                'user_id': data['user_id'],
                'success': False,
                'error': 'Bot blocked by user'
            })
            print(f"❌ Пользователь {data['user_id']} заблокировал бота")

        except Exception as e:
            results.append({
                'user_id': data['user_id'],
                'success': False,
                'error': str(e)
            })
            print(f"❌ Ошибка для пользователя {data['user_id']}: {e}")

    await bot.session.close()
    return results


# Расширенный вариант с клавиатурой
async def send_message_with_keyboard(bot_token: str, user_id: int, message: str):
    """
    Отправляет сообщение с inline клавиатурой
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    bot = Bot(token=bot_token)

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Кнопка 1", callback_data="btn_1"),
            InlineKeyboardButton(text="Кнопка 2", callback_data="btn_2")
        ],
        [
            InlineKeyboardButton(text="Ссылка", url="https://example.com")
        ]
    ])

    try:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        print("✅ Сообщение с клавиатурой отправлено!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


# Основная функция для примера использования
async def main():
    # Настройки
    BOT_TOKEN = "7847078425:AAFTT23UkslfYPaJjZ-mBa1khehB05mpQ3s"  # Замените на токен вашего бота
    USER_ID = 7210555334  # Замените на реальный Telegram ID

    # Пример 1: Простое сообщение
    await send_message_to_user(
        bot_token=BOT_TOKEN,
        user_id=USER_ID,
        message="<b>Добрый день! Это ZK Trade Bot.</b> К сожалению, Ваш контакт не указан в заказе. Обратитесь, пожалуйста, в поддержку для уточнения заказа - <a>@ukeubhjkrh</a>\n"
    )

    # Пример 2: Отправка нескольким пользователям
    messages = [
        {'user_id': 5190235975, 'text': 'Ку-ку'},
    ]

    # results = await send_multiple_messages(BOT_TOKEN, messages)
    # print(f"\nРезультаты отправки: {results}")

    # Пример 3: Сообщение с клавиатурой
    # await send_message_with_keyboard(
    #     bot_token=BOT_TOKEN,
    #     user_id=USER_ID,
    #     message="Выберите действие:"
    # )


if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())
