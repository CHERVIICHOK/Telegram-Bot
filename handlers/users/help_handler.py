from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging
from datetime import datetime

from config import TECHNICAL_SUPPORT
from keyboards.users.help_keyboards import (
    get_help_menu_keyboard,
    get_back_to_help_keyboard,
    get_contact_support_keyboard,
    get_rating_keyboard
)
from keyboards.users.keyboards import main_menu_keyboard
from states.help_state import HelpState

router = Router()
logger = logging.getLogger(__name__)


# Обработчик для команды "Помощь" из главного меню
@router.message(F.text == "❓ Помощь")
async def show_help_menu(message: Message, state: FSMContext):
    await state.set_state(HelpState.main_help)
    await message.answer(
        "Добро пожаловать в раздел помощи! Выберите интересующий вас вопрос:",
        reply_markup=get_help_menu_keyboard()
    )


# Обработчик для возврата в раздел помощи
@router.callback_query(F.data == "back_to_help")
async def back_to_help(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.main_help)
    await callback.message.edit_text(
        "Добро пожаловать в раздел помощи! Выберите интересующий вас вопрос:",
        reply_markup=get_help_menu_keyboard()
    )
    await callback.answer()


# Обработчик для возврата в главное меню
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Вы вернулись в главное меню", reply_markup=main_menu_keyboard)
    await callback.message.delete()
    await callback.answer()


# Обработчик для FAQ
@router.callback_query(F.data == "help_faq")
async def show_faq(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.faq)
    faq_text = """
📌 Часто задаваемые вопросы:

1️⃣ Как сделать заказ?  
- Выберете товар из каталога и добавьте в корзину.
- Нажмите кнопку «Корзина» → «Перейти к оформлению».  
- Укажите данные, которые попросит бот, подтвердите заказ, и ваш заказ отправится на обработку.  

2️⃣ Сколько стоит доставка?
Подробности можно узнать в разделе "Информация о доставке".

3️⃣ Какие способы оплаты доступны?
- После подтверждения заказа с вами свяжется один из менеджеров.
- Выберите удобный способ оплаты.
- Оплата при получении.
Более подробная информация - в разделе "Способы оплаты".

4️⃣ Как узнать статус моего заказа?
Статус заказа можно отслеживать в разделе "Профиль" → "Мои заказы".
    - «Принят на обработку» – заказ обрабатывается, ожидайте (примерное время ожидания: 10 минут).  
    - «Подтвержден» – заказ принят.  
    - «В сборке» – заказ собирается. 
    - «Передан курьеру» - заказ передан в доставку.
    - «Отправлен» - курьер выехал на заказ. 
    - «Доставлен» - заказ отдан и оплачен.

4️⃣ Есть проблема с заказом?  
Если товар не пришел, поврежден или возникли другие вопросы:  
    - Напишите в поддержку через кнопку «Связаться с поддержкой».  
    - Укажите номер заказа, ваше имя, ссылку на Telegram-аккаунт и описание проблемы.
"""
    await callback.message.edit_text(faq_text, reply_markup=get_back_to_help_keyboard())
    await callback.answer()


# Обработчик для контакта с поддержкой
@router.callback_query(F.data == "help_contact")
async def show_contact_support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.contact_support)
    contact_text = """
📞 Связь с поддержкой:

🕙 Часы работы поддержки: ежедневно с 10:00 до 22:00.

Нажмите, чтобы написать менеджеру:
"""
    await callback.message.edit_text(contact_text, reply_markup=get_contact_support_keyboard())
    await callback.answer()


# Обработчик для информации о доставке
@router.callback_query(F.data == "help_delivery")
async def show_delivery_info(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.delivery_info)
    delivery_text = """
🚚 Информация о доставке:

✅ Доставка по г. Казань полностью бесплатная!
"""
    await callback.message.edit_text(delivery_text, reply_markup=get_back_to_help_keyboard())
    await callback.answer()


# Обработчик для информации об оплате
@router.callback_query(F.data == "help_payment")
async def show_payment_info(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.payment_info)
    payment_text = """
💳 Способы оплаты:

✅ Банковской картой при получении
✅ Наличными при получении
✅ СБП (Система Быстрых Платежей)

💰 Оплата производится в рублях.
🔒 Все платежи защищены и обрабатываются надежными платежными системами.
"""
    await callback.message.edit_text(payment_text, reply_markup=get_back_to_help_keyboard())
    await callback.answer()


# Обработчик для информации о возврате
@router.callback_query(F.data == "help_refund")
async def show_refund_policy(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.refund_policy)
    refund_text = """
↩️ Политика возврата:

✅ Возврат товара возможен в течение одного дня с момента получения.
✅ Товар должен быть в неповрежденной упаковке и не использованным.
✅ Для оформления возврата свяжитесь с нашей службой поддержки.

📝 Для возврата необходимо предоставить:
    • Чек или подтверждение покупки
    • Причину возврата
    • Реквизиты для возврата средств
"""
    await callback.message.edit_text(refund_text, reply_markup=get_back_to_help_keyboard())
    await callback.answer()


@router.callback_query(F.data == "help_feedback")
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpState.feedback_comment)
    await callback.message.edit_text(
        "Мы будем благодарны за ваш отзыв о работе бота!\n\n"
        "Пожалуйста, напишите ваш комментарий о функционале бота. "
        "Что вам понравилось или не понравилось? Что можно улучшить?",
        reply_markup=get_back_to_help_keyboard()
    )
    await callback.answer()


@router.message(HelpState.feedback_comment)
async def process_feedback_comment(message: Message, state: FSMContext):
    # Сохраняем комментарий и информацию о пользователе в состоянии
    user = message.from_user
    user_info = f"@{user.username}" if user.username else f"{user.first_name} {user.last_name or ''}"

    await state.update_data(
        comment=message.text,
        user_id=user.id,
        user_info=user_info
    )

    await message.answer(
        "Спасибо за ваш комментарий!\n\n"
        "Теперь, пожалуйста, оцените функционал бота по 5-балльной шкале:",
        reply_markup=get_rating_keyboard()
    )
    await state.set_state(HelpState.feedback_rating)


@router.callback_query(HelpState.feedback_rating, F.data.startswith("rating_"))
async def process_rating(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Извлекаем оценку из callback_data
    rating = int(callback.data.split("_")[1])
    user_data = await state.get_data()

    # Получаем данные из состояния
    comment = user_data.get("comment", "")
    user_id = user_data.get("user_id")
    user_info = user_data.get("user_info")

    # Сохраняем отзыв и отправляем админам
    await save_feedback(user_id, comment, rating)
    await send_feedback_to_admins(bot, user_id, user_info, comment, rating)

    # Выводим пользователю уведомление
    stars = "⭐" * rating
    await callback.message.edit_text(
        f"Спасибо за вашу оценку: {rating} {stars}\n\n"
        f"Ваш комментарий и оценка помогут нам сделать бота еще лучше!",
        reply_markup=get_back_to_help_keyboard()
    )
    await callback.answer()


async def save_feedback(user_id, comment, rating):
    """
    Сохранение отзыва пользователя.
    """
    logger.info(f"Получен отзыв от пользователя {user_id}: Оценка {rating}, Комментарий: {comment}")

    # В реальной реализации здесь может быть код для сохранения в БД
    # Например:
    # from database.users.database_connection import get_connection
    # conn = await get_connection()
    # cursor = conn.cursor()
    # try:
    #     cursor.execute(
    #         "INSERT INTO user_feedback (user_id, comment, rating, created_at) "
    #         "VALUES (?, ?, ?, datetime('now'))",
    #         (user_id, comment, rating)
    #     )
    #     conn.commit()
    # except Exception as e:
    #     conn.rollback()
    #     logger.error(f"Ошибка при сохранении отзыва: {e}")
    # finally:
    #     cursor.close()
    #     conn.close()


async def send_feedback_to_admins(bot: Bot, user_id, user_info, comment, rating):
    """
    Отправка отзыва всем администраторам из списка TECHNICAL_SUPPORT
    """
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    stars = "⭐" * rating

    feedback_message = (
        f"📢 НОВЫЙ ОТЗЫВ О БОТЕ 📢\n\n"
        f"👤 Пользователь: {user_info} (ID: {user_id})\n"
        f"⏰ Время: {current_time}\n"
        f"⭐ Оценка: {rating}/5 {stars}\n\n"
        f"💬 Комментарий:\n{comment}"
    )

    for admin_id in TECHNICAL_SUPPORT:
        try:
            await bot.send_message(admin_id, feedback_message)
            logger.info(f"Отзыв отправлен администратору {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке отзыва администратору {admin_id}: {e}")
