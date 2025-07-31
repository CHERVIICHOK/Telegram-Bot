import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from database.admins.orders_bd import delete_order_by_id, get_order_by_id
from database.admins.staff_db import get_staff_by_role
from database.admins.users_db import get_username_by_telegram_id
from database.users.profile_db import (
    get_active_orders, get_all_orders, get_order_details, add_items_to_cart_from_order,
    should_send_notification, get_product_info_from_order
)
from database.users.reviews_db import (
    add_product_review,
    add_delivery_comment,
    has_product_review, has_delivery_comment
)
from states.profile_state import ProfileStates
from keyboards.users.profile_keyboards import (
    get_profile_keyboard, get_order_detail_keyboard, get_support_keyboard, get_status_emoji,
    get_active_order_list_keyboard, get_delivered_order_list_keyboard, get_delivery_rating_keyboard,
    get_product_list_keyboard, get_product_rating_keyboard, get_comment_keyboard, get_active_order_detail_keyboard,
    get_delivered_order_detail_keyboard
)
from keyboards.users.keyboards import main_menu_keyboard

profile_router = Router()

logger = logging.getLogger(__name__)


# Обработчик для текстовой кнопки профиля из главного меню
@profile_router.message(F.text == "👤 Профиль")
async def profile_text_button(message: Message, state: FSMContext):
    await show_profile_menu(message, state)


# Обработчик команды /profile
@profile_router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    await show_profile_menu(message, state)


# Обработчик кнопки "Личный кабинет" из главного меню
@profile_router.callback_query(F.data == "menu:profile")
async def profile_from_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_profile_menu(callback.message, state)


# Функция отображения меню личного кабинета
async def show_profile_menu(message: Message, state: FSMContext):
    await state.set_state(ProfileStates.MAIN)
    await message.answer(
        "👤 *Личный кабинет*\n\n"
        "Здесь вы можете отслеживать свои заказы, просматривать историю, оценивать товары и курьерскую службу.",
        reply_markup=get_profile_keyboard(),
        parse_mode="Markdown"
    )


# Обработка кнопки "Отследить заказ"
@profile_router.callback_query(F.data == "profile:track_orders")
async def track_orders(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ProfileStates.TRACKING_ORDERS)

    # Получение активных заказов пользователя
    active_orders = get_active_orders(callback.from_user.id)

    if not active_orders:
        await callback.message.edit_text(
            "🔍 *Отслеживание заказов*\n\n"
            "У вас нет активных заказов.",
            reply_markup=get_profile_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "🔍 *Отслеживание заказов*\n\n"
            "Выберите заказ для просмотра деталей:",
            reply_markup=get_active_order_list_keyboard(active_orders),
            parse_mode="Markdown"
        )


# Обработка выбора заказа для отслеживания
@profile_router.callback_query(F.data.startswith("profile:track_order_"))
async def show_tracked_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ProfileStates.ORDER_DETAIL)

    order_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    await state.update_data(current_order_id=order_id, from_tracking=True)

    order_details = get_order_details(order_id)

    if not order_details:
        await callback.message.edit_text(
            "❌ Заказ не найден.",
            reply_markup=get_profile_keyboard()
        )
        return

    # Формируем текст с деталями заказа
    emoji = get_status_emoji(order_details['status'])
    items_text = "\n".join([
        f"• {item['name']} x{item['quantity']} - {item['price']} ₽" for item in order_details['items']
    ])

    if not order_details['discount'] or order_details['discount'] == 0:
        text = (
            f"🔍 <b>Заказ #{order_details['user_order_id']}</b>\n\n"
            f"<b>Статус:</b> {emoji} {order_details['status']}\n"
            f"<b>Дата создания:</b> {order_details['creation_date']}\n"
            f"<b>Способ оплаты:</b> {order_details['payment_method']}\n"
            f"<b>Адрес доставки:</b> {order_details['delivery_address']}\n"
            f"<b>Сумма заказа:</b> {order_details['total_amount']} ₽\n\n"
            f"<b>Состав заказа:</b>\n{items_text}"
        )
    else:
        text = (
            f"🔍 <b>Заказ #{order_details['user_order_id']}</b>\n\n"
            f"<b>Статус:</b> {emoji} {order_details['status']}\n"
            f"<b>Дата создания:</b> {order_details['creation_date']}\n"
            f"<b>Способ оплаты:</b> {order_details['payment_method']}\n"
            f"<b>Адрес доставки:</b> {order_details['delivery_address']}\n"
            f"<b>Ваша скидка:</b> {order_details['discount']}\n"
            f"<b>Итоговая стоимость:</b> <s>{order_details['total_amount']}₽</s> → {order_details['total_amount'] - order_details['discount']}₽\n\n"
            f"<b>Состав заказа:</b>\n{items_text}"
        )

    is_active = order_details['status'] != "Доставлен"
    can_cancel = is_active  # Можно отказаться только от активного заказа

    await callback.message.edit_text(
        text,
        reply_markup=get_active_order_detail_keyboard(order_id, order_details['user_order_id'], is_active, can_cancel),
        parse_mode="HTML"
    )


@profile_router.callback_query(F.data.startswith("profile:cancel_order_"))
async def ask_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])

    order = get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    user_order_id = order.get("user_order_id")

    # Показываем подтверждение
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Нет, не отменять",
                    callback_data=f"profile:cancel_cancel_order_{order_id}"
                ),
                InlineKeyboardButton(
                    text="✅ Да, отказаться",
                    callback_data=f"profile:confirm_cancel_order_{order_id}"
                ),
            ]
        ]
    )
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите отказаться от заказа #{user_order_id}?\n"
        "Это действие необратимо.",
        reply_markup=keyboard
    )
    await callback.answer()


@profile_router.callback_query(F.data.startswith("profile:confirm_cancel_order_"))
async def confirm_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])

    order = get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден! Обратитесь в поддержку", show_alert=True)
        return

    success = delete_order_by_id(order_id)

    user_order_id = order.get("user_order_id")
    user_id = order.get("user_id")
    user_name = get_username_by_telegram_id(user_id)

    admin_note = (
        f"🛎️ Уведомление от бота. <b>Отмена заказа</b>\n\n"
        f"Пользователь <a>{user_id}</a> отменил заказ <b>№{order_id}</b>.\n\n\n"
        f"ℹ️ Контактная информация:\n"
        f"     Имя: {order.get('name')}\n"
        f"     Номер телефона: {order.get('phone')}\n"
        f"     Контакт для связи: https://t.me/{user_name}\n"
        f"     Telegram ID: {user_id}\n\n"
        f"Заказ был создан {order.get('created_at')}\n"
        f"Последний статус: {order.get('status')}"
    )

    if success:
        admins = get_staff_by_role(role="Админ")
        couriers = get_staff_by_role(role="Курьер")

        admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
        couriers_ids = [courier['telegram_id'] for courier in couriers if courier.get('is_active', 1)]

        for admin_id in admin_ids:
            try:
                await callback.bot.send_message(
                    admin_id,
                    admin_note,
                    parse_mode="HTML"
                )
                logger.info(f"SUCCESS: информация об отмене заказа отправлена администратору {admin_id}")
            except Exception as e:
                logger.error(f"FAIL: не удалось информация об отмене заказа администратору {admin_id}: {e}")

        for couriers_id in couriers_ids:
            try:
                await callback.bot.send_message(
                    couriers_id,
                    admin_note,
                    parse_mode="HTML"
                )
                logger.info(f"SUCCESS: информация об отмене заказа отправлена администратору {couriers_id}")
            except Exception as e:
                logger.error(f"FAIL: не удалось информация об отмене заказа администратору {couriers_id}: {e}")

        await callback.message.edit_text(
            f"✅ Ваш заказ #{user_order_id} был успешно отменён.",
            reply_markup=get_profile_keyboard()
        )
        await callback.answer("☑️ Заказ отменён", show_alert=True)
    else:
        await callback.answer("Не удалось отменить заказ!", show_alert=True)


@profile_router.callback_query(F.data.startswith("profile:cancel_cancel_order_"))
async def cancel_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    order_details = get_order_details(order_id)
    if not order_details:
        await callback.message.edit_text(
            "❌ Заказ не найден.",
            reply_markup=get_profile_keyboard()
        )
        return

    emoji = get_status_emoji(order_details['status'])
    items_text = "\n".join([
        f"• {item['name']} x{item['quantity']} - {item['price']} ₽" for item in order_details['items']
    ])

    if not order_details['discount'] or order_details['discount'] == 0:
        text = (
            f"🔍 <b>Заказ #{order_details['user_order_id']}</b>\n\n"
            f"<b>Статус:</b> {emoji} {order_details['status']}\n"
            f"<b>Дата создания:</b> {order_details['creation_date']}\n"
            f"<b>Способ оплаты:</b> {order_details['payment_method']}\n"
            f"<b>Адрес доставки:</b> {order_details['delivery_address']}\n"
            f"<b>Сумма заказа:</b> {order_details['total_amount']} ₽\n\n"
            f"<b>Состав заказа:</b>\n{items_text}"
        )
    else:
        text = (
            f"🔍 <b>Заказ #{order_details['user_order_id']}</b>\n\n"
            f"<b>Статус:</b> {emoji} {order_details['status']}\n"
            f"<b>Дата создания:</b> {order_details['creation_date']}\n"
            f"<b>Способ оплаты:</b> {order_details['payment_method']}\n"
            f"<b>Адрес доставки:</b> {order_details['delivery_address']}\n"
            f"<b>Ваша скидка:</b> {order_details['discount']}\n"
            f"<b>Итоговая стоимость:</b> <s>{order_details['total_amount']}₽</s> → {order_details['total_amount'] - order_details['discount']}₽\n\n"
            f"<b>Состав заказа:</b>\n{items_text}"
        )

    is_active = order_details['status'] != "Доставлен"
    can_cancel = is_active

    await callback.message.edit_text(
        text,
        reply_markup=get_order_detail_keyboard(order_id, is_active, can_cancel=can_cancel),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработка кнопки "История заказов"
@profile_router.callback_query(F.data == "profile:order_history")
async def order_history(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ProfileStates.ORDER_HISTORY)

    all_orders = get_all_orders(callback.from_user.id)

    if not all_orders:
        await callback.message.edit_text(
            "📋 *История заказов*\n\n"
            "У вас еще нет заказов.",
            reply_markup=get_profile_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "📋 *История заказов*\n\n"
            "Выберите заказ для просмотра деталей:",
            reply_markup=get_delivered_order_list_keyboard(all_orders, prefix="history"),
            parse_mode="Markdown"
        )


# Обработка выбора заказа из истории
@profile_router.callback_query(F.data.startswith("profile:history_order_"))
async def show_history_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ProfileStates.ORDER_DETAIL)

    order_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    await state.update_data(current_order_id=order_id, from_tracking=False)

    order_details = get_order_details(order_id)

    if not order_details:
        await callback.message.edit_text(
            "❌ Заказ не найден.",
            reply_markup=get_profile_keyboard()
        )
        return

    # Формируем текст с деталями заказа
    emoji = get_status_emoji(order_details['status'])
    items_text = "\n".join([
        f"• {item['name']} x{item['quantity']} - {item['price']} ₽"
        for item in order_details['items']
    ])

    if not order_details['discount'] or order_details['discount'] == 0:
        text = (
            f"📋 <b>Заказ #{order_details['user_order_id']}</b>\n\n"
            f"<b>Статус:</b> {emoji} {order_details['status']}\n"
            f"<b>Дата создания:</b> {order_details['creation_date']}\n"
            f"<b>Способ оплаты:</b> {order_details['payment_method']}\n"
            f"<b>Адрес доставки:</b> {order_details['delivery_address']}\n"
            f"<b>Сумма заказа:</b> {order_details['total_amount']} ₽\n\n"
            f"<b>Состав заказа</b> \n{items_text}"
        )
    else:
        text = (
            f"🔍 <b>Заказ #{order_details['user_order_id']}</b>\n\n"
            f"<b>Статус:</b> {emoji} {order_details['status']}\n"
            f"<b>Дата создания:</b> {order_details['creation_date']}\n"
            f"<b>Способ оплаты:</b> {order_details['payment_method']}\n"
            f"<b>Адрес доставки:</b> {order_details['delivery_address']}\n"
            f"<b>Ваша скидка:</b> {order_details['discount']}\n"
            f"<b>Итоговая стоимость:</b> <s>{order_details['total_amount']}₽</s> → {order_details['total_amount'] - order_details['discount']}₽\n\n"
            f"<b>Состав заказа:</b> \n{items_text}"
        )

    is_delivered = order_details['status'] == "Доставлен"
    delivery_rated = has_delivery_comment(user_id, order_id)
    products_rated = all(
        has_product_review(user_id, item['product_id']) for item in order_details['items'])  # Теперь тут проверка

    await callback.message.edit_text(
        text,
        reply_markup=get_delivered_order_detail_keyboard(
            order_id,
            order_details['user_order_id'],
            delivery_rated=delivery_rated,
            products_rated=products_rated
        ),
        parse_mode="HTML"
    )


# Обработка кнопки "Повторить заказ"
@profile_router.callback_query(F.data.startswith("profile:repeat_order_"))
async def repeat_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Товары добавлены в корзину!")

    order_id = int(callback.data.split("_")[-1])
    add_items_to_cart_from_order(callback.from_user.id, order_id)

    # Перенаправляем пользователя в корзину
    from handlers.users.cart import show_cart
    await show_cart(callback, state)


# Обработчик кнопки "Оценить доставку"
@profile_router.callback_query(F.data.startswith("profile:rate_delivery_"))
async def rate_delivery(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    order_id = int(callback.data.split("_")[-1])

    # Проверяем, оставлял ли пользователь отзыв о доставке
    if has_delivery_comment(user_id, order_id):
        await callback.answer("Вы уже оценили доставку для этого заказа!", show_alert=True)
        return

    await callback.answer()
    await state.update_data(current_order_id=order_id)
    await state.set_state(ProfileStates.WAITING_FOR_DELIVERY_RATING)
    await callback.message.edit_text(
        "Оцените, пожалуйста, качество доставки:",
        reply_markup=get_delivery_rating_keyboard(order_id)
    )


# Обработчик выбора рейтинга доставки
@profile_router.callback_query(F.data.startswith("profile:delivery_rating_"),
                               ProfileStates.WAITING_FOR_DELIVERY_RATING)
async def delivery_rating_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    rating = int(callback.data.split("_")[3])
    await state.update_data(delivery_rating=rating)
    await state.set_state(ProfileStates.WAITING_FOR_DELIVERY_COMMENT)

    # Создаем клавиатуру с кнопкой "Пропустить"
    keyboard = get_comment_keyboard(skip_callback=f"profile:skip_delivery_comment_{order_id}")

    await callback.message.edit_text(
        "Пожалуйста, оставьте комментарий о доставке (или пропустите этот шаг):",
        reply_markup=keyboard
    )


# Обработчик комментария о доставке
@profile_router.message(ProfileStates.WAITING_FOR_DELIVERY_COMMENT, F.text)
async def delivery_comment_received(message: Message, state: FSMContext, bot: Bot):  # Добавили bot: Bot
    user_id = message.from_user.id
    username = message.from_user.username
    comment = message.text
    data = await state.get_data()
    order_id = data.get("current_order_id")
    rating = data.get("delivery_rating")

    # Сохраняем оценку и комментарий в базу данных
    add_delivery_comment(user_id=user_id, order_id=order_id, rating=rating, comment=comment)

    await message.reply("Спасибо за ваш отзыв о доставке!")
    await state.clear()

    # Получаем информацию о заказе
    order_details = get_order_details(order_id)
    if not order_details:
        await message.answer(
            "Не удалось получить информацию о заказе."
        )
        return

    # Формируем текст уведомления для админов
    message_text = (
        f"<b>Новый отзыв о доставке!</b>\n\n"
        f"<b>Пользователь:</b> <a href='tg://user?id={user_id}'>@{username or user_id}</a> (<code>{user_id}</code>)\n"
        f"<b>Заказ №:</b> {order_details['order_id']}\n"
        f"<b>Оценка доставки:</b> {rating} ⭐\n"
    )
    if comment:
        message_text += f"<b>Комментарий:</b> {comment}\n"

    # Отправляем уведомление всем админам
    try:
        admins = get_staff_by_role(role="Админ")
        admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
        for admin_id in admin_ids:
            await bot.send_message(
                admin_id,
                message_text,
                parse_mode="HTML"
            )

        logger.info(f"Отправлено уведомление об отзыве о доставке для заказа {order_details['user_order_id']}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об отзыве о доставке: {e}")

    await message.answer(
        text="Профиль",
        reply_markup=get_profile_keyboard()
    )


# Обработчик кнопки "Оценить товары"
@profile_router.callback_query(F.data.startswith("profile:rate_product_list_"))
async def rate_product_list(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    order_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    await state.update_data(current_order_id=order_id)
    await state.set_state(ProfileStates.WAITING_FOR_PRODUCT_LIST)

    order_details = get_product_info_from_order(order_id)

    if not order_details:
        await callback.message.edit_text(
            "Не удалось получить информацию о товарах в заказе."
        )
        return

    # Фильтруем товары, чтобы оставить только те, которые еще не были оценены
    products_to_rate = [
        product for product in order_details
        if not has_product_review(user_id, product['product_id'])
    ]

    if not products_to_rate:
        await callback.message.edit_text(
            "Вы оценили все товары в этом заказе! Спасибо за ваши отзывы.",
            reply_markup=get_profile_keyboard()
        )
        await state.clear()  # Очищаем состояние
        return

    # Создаем клавиатуру со списком товаров
    keyboard = get_product_list_keyboard(order_id, products_to_rate)

    await callback.message.edit_text(
        "Выберите товар, который хотите оценить:",
        reply_markup=keyboard
    )


# Обработчик выбора товара для оценки
@profile_router.callback_query(F.data.startswith("profile:rate_product_"), ProfileStates.WAITING_FOR_PRODUCT_LIST)
async def rate_product(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id

    # Проверяем, оставлял ли пользователь отзыв об этом товаре
    if has_product_review(user_id, product_id):
        await callback.answer("Вы уже оценили этот товар!", show_alert=True)
        return

    await state.update_data(current_order_id=order_id, current_product_id=product_id)
    await state.set_state(ProfileStates.WAITING_FOR_PRODUCT_RATING)

    await callback.message.edit_text(
        f"Оцените, пожалуйста, товар ID {product_id}:",
        reply_markup=get_product_rating_keyboard(order_id, product_id)
    )


# Обработчик выбора рейтинга товара
@profile_router.callback_query(F.data.startswith("profile:product_rating_"),
                               ProfileStates.WAITING_FOR_PRODUCT_RATING)
async def product_rating_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    product_id = int(callback.data.split("_")[3])
    rating = int(callback.data.split("_")[4])
    await state.update_data(product_rating=rating)
    await state.set_state(ProfileStates.WAITING_FOR_PRODUCT_COMMENT)

    # Создаем клавиатуру с кнопкой "Пропустить"
    keyboard = get_comment_keyboard(skip_callback=f"profile:skip_product_comment_{order_id}_{product_id}")

    await callback.message.edit_text(
        "Пожалуйста, оставьте комментарий о товаре (или пропустите этот шаг):",
        reply_markup=keyboard
    )


# Обработчик комментария о товаре
@profile_router.message(ProfileStates.WAITING_FOR_PRODUCT_COMMENT, F.text)
async def product_comment_received(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    comment = message.text
    data = await state.get_data()
    order_id = data.get("current_order_id")
    product_id = data.get("current_product_id")
    rating = data.get("product_rating")

    # Сохраняем оценку и комментарий в базу данных
    add_product_review(user_id=user_id, product_id=product_id, rating=rating, comment=comment)

    await message.reply("Спасибо за ваш отзыв о товаре!")
    await state.clear()

    # Получаем информацию о заказе и товаре
    order_details = get_order_details(order_id)
    if not order_details:
        await message.answer(
            "Не удалось получить информацию о товарах в заказе."
        )
        return

    product = next((item for item in order_details['items'] if item['product_id'] == product_id), None)
    if not product:
        await message.answer(
            "Не удалось получить информацию о товаре."
        )
        return

    message_text = (
        f"<b>Новый отзыв о товаре!</b>\n\n"
        f"<b>Пользователь:</b> <a href='tg://user?id={user_id}'>@{username or user_id}</a> (<code>{user_id}</code>)\n"
        f"<b>Заказ №:</b> {order_details['order_id']}\n"
        f"<b>Товар:</b> {product['name']}\n"
        f"<b>Оценка:</b> {rating} ⭐\n"
    )
    if comment:
        message_text += f"<b>Комментарий:</b> {comment}\n"

    # Отправляем уведомление всем админам
    try:
        admins = get_staff_by_role(role="Админ")
        admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
        for admin_id in admin_ids:
            await bot.send_message(
                admin_id,
                message_text,
                parse_mode="HTML"
            )

        logger.info(f"Отправлено уведомление об отзыве о товаре {product['name']} (ID {product_id})")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об отзыве о товаре: {e}")

    # Возвращаемся к списку товаров для оценки
    order_details = get_product_info_from_order(order_id)
    if not order_details:
        await message.answer(
            "Не удалось получить информацию о товарах в заказе."
        )
        return

    # Фильтруем товары, чтобы оставить только те, которые еще не были оценены
    products_to_rate = [
        product for product in order_details
        if not has_product_review(user_id, product['product_id'])
    ]

    if not products_to_rate:
        await message.answer(
            "Вы оценили все товары в этом заказе! Спасибо за ваши отзывы.",
            reply_markup=get_profile_keyboard()
        )
        await state.clear()  # Очищаем состояние
        return

    keyboard = get_product_list_keyboard(order_id, products_to_rate)
    await state.set_state(ProfileStates.WAITING_FOR_PRODUCT_LIST)  # Устанавливаем состояние
    await message.answer(
        text="Выберите товар, который хотите оценить:",
        reply_markup=keyboard
    )


# Обработчик "Пропустить" для комментария о доставке
@profile_router.callback_query(F.data.startswith("profile:skip_delivery_comment_"),
                               ProfileStates.WAITING_FOR_DELIVERY_COMMENT)
async def skip_delivery_comment(callback: CallbackQuery, state: FSMContext, bot: Bot):  # Добавили bot: Bot
    await callback.answer("Вы пропустили написание комментария о доставке.")
    user_id = callback.from_user.id
    username = callback.from_user.username  # Получаем username
    data = await state.get_data()
    order_id = data.get("current_order_id")
    rating = data.get("delivery_rating")  # Получаем рейтинг из state

    # Сохраняем только факт, что пропустили комментарий
    add_delivery_comment(user_id=user_id, order_id=order_id, rating=rating, comment="Комментарий пропущен")

    # Получаем информацию о заказе
    order_details = get_order_details(order_id)
    if not order_details:
        await callback.message.answer(
            "Не удалось получить информацию о заказе."
        )
        return

    # Формируем текст уведомления для админов
    message_text = (
        f"<b>Новый отзыв о доставке (комментарий пропущен)!</b>\n\n"
        f"<b>Пользователь:</b> <a href='tg://user?id={user_id}'>@{username or user_id}</a> (<code>{user_id}</code>)\n"
        f"<b>Заказ №:</b> {order_details['order_id']}\n"
        f"<b>Оценка доставки:</b> {rating} ⭐\n"
        f"<b>Комментарий:</b> <i>Пропущен</i>\n"
    )

    # Отправляем уведомление всем админам
    try:
        admins = get_staff_by_role(role="Админ")
        admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
        for admin_id in admin_ids:
            await bot.send_message(
                admin_id,
                message_text,
                parse_mode="HTML"
            )

        logger.info(f"Отправлено уведомление о пропуске отзыва о доставке для заказа {order_details['user_order_id']}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о пропуске отзыва о доставке: {e}")

    await state.clear()

    await callback.message.edit_text(
        text="Профиль",
        reply_markup=get_profile_keyboard()
    )


# Обработчик "Пропустить" для комментария о товаре
@profile_router.callback_query(F.data.startswith("profile:skip_product_comment_"),
                               ProfileStates.WAITING_FOR_PRODUCT_COMMENT)
async def skip_product_comment(callback: CallbackQuery, state: FSMContext, bot: Bot):  # Добавили bot: Bot
    await callback.answer("Вы пропустили написание комментария о товаре.")
    user_id = callback.from_user.id
    username = callback.from_user.username  # Получаем username
    data = await state.get_data()
    order_id = data.get("current_order_id")
    product_id = data.get("current_product_id")
    rating = data.get("product_rating")  # Получаем рейтинг из state

    # Сохраняем только факт, что пропустили комментарий
    add_product_review(user_id=user_id, product_id=product_id, rating=rating, comment="Комментарий пропущен")

    # Получаем информацию о заказе и товаре
    order_details = get_order_details(order_id)
    if not order_details:
        await callback.message.answer(
            "Не удалось получить информацию о товарах в заказе."
        )
        return

    product = next((item for item in order_details['items'] if item['product_id'] == product_id), None)
    if not product:
        await callback.message.answer(
            "Не удалось получить информацию о товаре."
        )
        return

    # Формируем текст уведомления для админов
    message_text = (
        f"<b>Новый отзыв о товаре (комментарий пропущен)!</b>\n\n"
        f"<b>Пользователь:</b> <a href='tg://user?id={user_id}'>@{username or user_id}</a> (<code>{user_id}</code>)\n"
        f"<b>Заказ №:</b> {order_details['order_id']}\n"
        f"<b>Товар:</b> {product['name']}\n"
        f"<b>Оценка:</b> {rating} ⭐\n"
        f"<b>Комментарий:</b> <i>Пропущен</i>\n"
    )

    # Отправляем уведомление всем админам
    try:
        admins = get_staff_by_role(role="Админ")
        admin_ids = [admin['telegram_id'] for admin in admins if admin.get('is_active', 1)]
        for admin_id in admin_ids:
            await bot.send_message(
                admin_id,
                message_text,
                parse_mode="HTML"
            )

        logger.info(f"Отправлено уведомление о пропуске отзыва о товаре {product['name']} (ID {product_id})")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о пропуске отзыва о товаре: {e}")

    order_details = get_product_info_from_order(order_id)
    if not order_details:
        await callback.message.answer(
            "Не удалось получить информацию о товарах в заказе."
        )
        return

    # Фильтруем товары, чтобы оставить только те, которые еще не были оценены
    products_to_rate = [
        product for product in order_details
        if not has_product_review(user_id, product['product_id'])
    ]

    if not products_to_rate:
        await callback.message.edit_text(
            text="Вы оценили все товары в этом заказе! Спасибо за ваши отзывы.",
            reply_markup=get_profile_keyboard()
        )
        await state.clear()  # Очищаем состояние
        return

    keyboard = get_product_list_keyboard(order_id, products_to_rate)
    await state.set_state(ProfileStates.WAITING_FOR_PRODUCT_LIST)  # Устанавливаем состояние
    await callback.message.edit_text(
        text="Выберите товар, который хотите оценить:",
        reply_markup=keyboard
    )


# Обработка кнопки "Связаться с поддержкой"
@profile_router.callback_query(F.data.startswith("profile:support_"))
async def contact_support(callback: CallbackQuery):
    await callback.answer()

    order_id = int(callback.data.split("_")[-1])

    await callback.message.edit_text(
        "📞 *Связь с поддержкой*\n\n"
        f"Если у вас возникли вопросы по заказу #{order_id}, "
        "вы можете связаться с нашим оператором поддержки.",
        reply_markup=get_support_keyboard(order_id),
        parse_mode="Markdown"
    )


# Обработчики кнопок "Назад"
@profile_router.callback_query(F.data == "profile:back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_profile_menu(callback.message, state)


@profile_router.callback_query(F.data == "profile:back_to_orders")
async def back_to_orders(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    from_tracking = data.get('from_tracking', True)

    if from_tracking:
        await track_orders(callback, state)
    else:
        await order_history(callback, state)


@profile_router.callback_query(F.data.startswith("profile:back_to_order_"))
async def back_to_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    order_id = int(callback.data.split("_")[-1])
    await state.update_data(current_order_id=order_id)

    # Получаем данные о том, из какого списка был показан заказ
    data = await state.get_data()
    if data.get('from_tracking', True):
        await show_tracked_order(callback, state)
    else:
        await show_history_order(callback, state)


@profile_router.callback_query(F.data == "profile:back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.answer()

    # Возвращаем пользователя в главное меню бота
    await callback.message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=main_menu_keyboard
    )
    # Удаляем сообщение с инлайн-клавиатурой
    await callback.message.delete()


async def send_order_status_notification(bot, user_id, order_id, new_status):
    should_notify = should_send_notification(user_id)

    if should_notify:
        emoji = get_status_emoji(new_status)
        await bot.send_message(
            user_id,
            f"📢 *Уведомление о заказе*\n\n"
            f"Статус вашего заказа #{order_id} изменен на: {emoji} *{new_status}*",
            parse_mode="Markdown"
        )
