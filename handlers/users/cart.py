import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import os
from database.users import database as db
from keyboards.users.inline import create_cart_keyboard
from database.users.warehouse_connection import get_product_stock_quantity
from states.cart_state import CartState

router = Router()

logger = logging.getLogger(__name__)


@router.message(F.text == "🛒 Корзина")
async def cart_command(message: Message, state: FSMContext):
    logger.info("Получена команда /cart")

    # Устанавливаем состояние просмотра корзины
    await state.set_state(CartState.viewing_cart)
    await state.update_data(current_item_index=0, last_message_id=None, last_product_id=None)

    # Получаем данные для отображения первого товара
    cart_data = await show_cart_item(message.from_user.id)

    if cart_data["is_empty"]:
        await message.answer("Ваша корзина пуста. Добавьте товары из каталога!")
        await state.clear()
    else:
        if cart_data["photo"] and os.path.exists(cart_data["photo"]):
            with open(cart_data["photo"], 'rb') as photo:
                sent_message = await message.answer_photo(
                    photo=photo,
                    caption=cart_data["text"],
                    reply_markup=cart_data["reply_markup"],
                    parse_mode="HTML"
                )
                await state.update_data(last_message_id=sent_message.message_id,
                                        last_product_id=cart_data.get("product_id"))
        else:
            sent_message = await message.answer(
                text=cart_data["text"],
                reply_markup=cart_data["reply_markup"],
                parse_mode="HTML"
            )
            await state.update_data(last_message_id=sent_message.message_id,
                                    last_product_id=cart_data.get("product_id"))


# Обработчик для показа корзины через callback
@router.callback_query(F.data == "show_cart")
async def show_cart(callback: CallbackQuery, state: FSMContext):
    # logger.info(f"Получен callback: {callback.data}")
    await callback.answer()

    # Устанавливаем состояние просмотра корзины
    await state.set_state(CartState.viewing_cart)
    await state.update_data(current_item_index=0, last_message_id=None, last_product_id=None)

    # Получаем данные для отображения первого товара
    cart_data = await show_cart_item(callback.from_user.id)

    if cart_data["is_empty"]:
        await callback.message.answer("Ваша корзина пуста. Добавьте товары из каталога!")
        await state.clear()
    else:
        if cart_data["photo"] and os.path.exists(cart_data["photo"]):
            with open(cart_data["photo"], 'rb') as photo:
                sent_message = await callback.message.answer_photo(
                    photo=photo,
                    caption=cart_data["text"],
                    reply_markup=cart_data["reply_markup"],
                    parse_mode="HTML"
                )
                await state.update_data(last_message_id=sent_message.message_id,
                                        last_product_id=cart_data.get("product_id"))
        else:
            sent_message = await callback.message.answer(
                text=cart_data["text"],
                reply_markup=cart_data["reply_markup"],
                parse_mode="HTML"
            )
            await state.update_data(last_message_id=sent_message.message_id,
                                    last_product_id=cart_data.get("product_id"))


# Показ товара в корзине
async def show_cart_item(user_id, item_index=0):
    logger.info(f"Показываем корзину для пользователя {user_id}, индекс {item_index}")
    cart_items = db.get_cart_items(user_id)
    logger.info(f"Получены товары: {len(cart_items) if cart_items else 0}")

    if not cart_items:
        return {
            "text": "Ваша корзина пуста. Добавьте товары из каталога!",
            "photo": None,
            "reply_markup": None,
            "is_empty": True
        }

    # Ограничиваем индекс границами списка
    item_index = max(0, min(item_index, len(cart_items) - 1))
    current_item = cart_items[item_index]

    # Получаем информацию о товаре
    product_id = current_item['product_id']
    quantity = current_item['quantity']
    price = current_item['price']
    total_price = current_item['total_price']

    # Общая сумма корзины
    cart_total = sum(item['total_price'] for item in cart_items)

    # Доступное количество на складе
    stock_quantity = get_product_stock_quantity(product_id)

    # Форматируем цены
    price_formatted = format_price(price)
    total_item_formatted = format_price(total_price)
    cart_total_formatted = format_price(cart_total)

    # Собираем текст сообщения
    message_text = (
        f"<b>⎯⎯⎯⎯⎯⎯  Товар {item_index + 1} из {len(cart_items)}⎯⎯⎯⎯⎯⎯</b>\n\n"
        f"<b>Общая сумма корзины:</b> {cart_total_formatted}₽\n\n"
        f"<b>Название: {current_item['category']} {current_item['product_name']}</b>\n"
        f"<b>Вкус:</b> {current_item['flavor']}\n\n"
        f"<b>Цена:</b> {price_formatted}₽\n"
        f"<b>Количество:</b> {quantity} × {price_formatted}₽ = {total_item_formatted}₽\n\n"
    )

    # Получаем путь к изображению
    photo_path = os.path.join('database', 'images', f"{product_id}.jpg")
    # logger.info(f"Путь к фото: {photo_path}, существует: {os.path.exists(photo_path)}")

    # Создаем клавиатуру для корзины
    keyboard = create_cart_keyboard(
        current_quantity=quantity,
        current_index=item_index,
        total_items=len(cart_items),
        stock_quantity=stock_quantity,
        product_id=product_id
    )

    return {
        "text": message_text,
        "photo": photo_path if os.path.exists(photo_path) else None,
        "reply_markup": keyboard,
        "is_empty": False,
        "current_index": item_index,
        "product_id": product_id  # Добавляем ID товара для отслеживания
    }


# Форматирование цен с разделителями
def format_price(price):
    if isinstance(price, float) and price != int(price):
        # Для дробных цен
        return f"{int(price):,}".replace(",", " ") + f",{int((price % 1) * 100):02d}"
    else:
        # Для целых цен
        return f"{int(price):,}".replace(",", " ")


# Обработчик для кнопок корзины
@router.callback_query(F.data.startswith("cart:"))
async def process_cart_callback(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Получен callback корзины: {callback.data}")
    # await callback.answer()

    action = callback.data.split(":")
    action_type = action[1]
    product_id = int(action[2]) if len(action) > 2 else None

    # Получаем данные из состояния
    state_data = await state.get_data()
    current_index = state_data.get("current_item_index", 0)

    # Начальная обработка действий
    if action_type == "next":
        # Следующий товар
        current_index += 1
        await state.update_data(current_item_index=current_index)

    elif action_type == "prev":
        # Предыдущий товар
        current_index = max(0, current_index - 1)
        await state.update_data(current_item_index=current_index)

    elif action_type == "inc" and product_id:
        # Увеличение количества
        cart_items = db.get_cart_items(callback.from_user.id)
        for item in cart_items:
            if item['product_id'] == product_id:
                stock_quantity = get_product_stock_quantity(product_id)

                db.update_cart_item_quantity(
                    callback.from_user.id,
                    product_id,
                    item['quantity'] + 1
                )
                await callback.answer()
                logger.info(f"Увеличено количество товара {product_id} до {item['quantity'] + 1}")
                break

    elif action_type == "dec" and product_id:
        # Уменьшение количества
        cart_items = db.get_cart_items(callback.from_user.id)
        for item in cart_items:
            if item['product_id'] == product_id:
                if item['quantity'] > 1:
                    # Если больше 1, уменьшаем на 1
                    db.update_cart_item_quantity(
                        callback.from_user.id,
                        product_id,
                        item['quantity'] - 1
                    )
                    logger.info(f"Уменьшено количество товара {product_id} до {item['quantity'] - 1}")
                else:
                    # Если 1, удаляем товар
                    db.update_cart_item_quantity(callback.from_user.id, product_id, 0)
                    logger.info(f"Удален товар {product_id} из корзины")
                break

    elif action_type == "del" and product_id:
        # Удаление товара
        db.update_cart_item_quantity(callback.from_user.id, product_id, 0)
        logger.info(f"Удален товар {product_id} из корзины")
        # Проверяем, остались ли товары в корзине
        cart_items = db.get_cart_items(callback.from_user.id)
        if not cart_items:
            try:
                # Пробуем обновить подпись, если сообщение с фото
                await callback.message.edit_caption(caption="Ваша корзина пуста. Добавьте товары из каталога!")
            except Exception as e:
                try:
                    # Если не получилось, пробуем обновить текст
                    await callback.message.edit_text("Ваша корзина пуста. Добавьте товары из каталога!")
                except Exception:
                    # Если и это не сработало, отправляем новое сообщение
                    await callback.message.answer("Ваша корзина пуста. Добавьте товары из каталога!")
            await state.clear()
            return

    elif action_type == "main_menu":
        # Переход в главное меню
        try:
            # Удаляем клавиатуру и выводим сообщение
            await callback.message.edit_text(
                "Вы вернулись в главное меню",
                reply_markup=None  # Удаляем инлайн-клавиатуру
            )

            return
        except Exception as e:
            logger.info(f"Ошибка при переходе в главное меню: {e}")

    elif action_type == "catalog":
        # Переход в каталог
        try:
            from handlers.users.catalog import catalog_handler

            await callback.message.delete()

            await catalog_handler(callback.message, state)
            return  # Выходим из обработчика
        except Exception as e:
            logger.info(f"Ошибка при переходе в каталог: {e}")

    elif action_type == "checkout":
        # Оформление заказа
        try:
            # Импортируем обработчик оформления заказа
            from handlers.users.order import start_checkout
            # Вызываем функцию начала оформления заказа
            await start_checkout(callback, state)
        except Exception as e:
            logger.error(f"Ошибка при переходе к оформлению заказа: {e}")
            await callback.answer("Произошла ошибка при оформлении заказа. Попробуйте позже.")
        return  # Выходим из обработчика
    # Получаем актуальные данные после обработки действия
    cart_data = await show_cart_item(callback.from_user.id, current_index)

    if cart_data["is_empty"]:
        # Если корзина пуста
        try:
            await callback.message.edit_caption(caption="Ваша корзина пуста. Добавьте товары из каталога!")
        except Exception:
            await callback.message.edit_text("Ваша корзина пуста. Добавьте товары из каталога!")
        await state.clear()
        return

    # Всегда обновляем текст и клавиатуру для правильного отображения изменений
    try:
        # Пробуем обновить подпись под фото
        await callback.message.edit_caption(
            caption=cart_data["text"],
            reply_markup=cart_data["reply_markup"],
            parse_mode="HTML"
        )
    except Exception as e:
        logger.info(f"Ошибка при обновлении caption: {e}")
        try:
            # Если не удалось обновить подпись, возможно это текстовое сообщение
            await callback.message.edit_text(
                text=cart_data["text"],
                reply_markup=cart_data["reply_markup"],
                parse_mode="HTML"
            )
        except Exception as e:
            logger.info(f"Ошибка при обновлении текста: {e}")

            # Если и это не удалось, отправляем новое сообщение
            if cart_data["photo"] and os.path.exists(cart_data["photo"]):
                with open(cart_data["photo"], 'rb') as photo:
                    await callback.message.answer_photo(
                        photo=photo,
                        caption=cart_data["text"],
                        reply_markup=cart_data["reply_markup"],
                        parse_mode="HTML"
                    )
            else:
                await callback.message.answer(
                    text=cart_data["text"],
                    reply_markup=cart_data["reply_markup"],
                    parse_mode="HTML"
                )
