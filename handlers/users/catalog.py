import asyncio
import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from database.users import favorites_db
from database.users.favorites_db import add_product_to_favorites
from keyboards.users.keyboards import main_menu_keyboard
from keyboards.users.inline import (
    get_categories_keyboard,
    get_product_names_keyboard,
    get_product_details_keyboard, get_flavors_keyboard, get_flavor_actions_keyboard
)
from database.users.warehouse_connection import (
    fetch_categories,
    fetch_products_by_category_and_product_name,
    create_connection_warehouse, get_available_product_names, close_connection_warehouse,
    get_products_by_category_and_name, get_product_by_id
)
from database.users.database import add_to_cart
from states.catalog_state import CatalogState
import os

from utils.catalog_mapping import catalog_mapping

router = Router()

logger = logging.getLogger(__name__)


@router.message(F.text == "🛍️ Каталог товаров")
async def catalog_handler(message: Message, state: FSMContext):
    """Обработчик кнопки '🛍️ Каталог товаров'. Отображает список категорий."""
    await state.set_state(CatalogState.browsing_categories)
    categories = fetch_categories()
    if categories:
        markup = get_categories_keyboard(categories)
        await message.answer("Выберите категорию товаров:", reply_markup=markup)
    else:
        await message.answer("К сожалению, каталог товаров пуст.")


@router.callback_query(F.data == "start_catalog_browsing")
async def start_catalog_browsing_callback(query: CallbackQuery, state: FSMContext):
    """Обработчик callback для начала просмотра каталога (из других меню)."""
    await state.set_state(CatalogState.browsing_categories)
    categories = fetch_categories()
    if categories:
        markup = get_categories_keyboard(categories)
        await query.message.edit_text("Выберите категорию товаров:", reply_markup=markup)
    else:
        await query.message.edit_text("К сожалению, каталог товаров пуст.",
                                      reply_markup=None)

    await query.answer()


@router.callback_query(F.data.startswith("page:category:"))
async def category_pagination_handler(query: CallbackQuery):
    """Обработчик пагинации категорий"""
    page = int(query.data.split(":")[2])
    categories = fetch_categories()
    markup = get_categories_keyboard(categories, current_page=page)
    await query.message.edit_text("Выберите категорию товаров:", reply_markup=markup)
    await query.answer()


@router.callback_query(F.data.startswith("page:"))
async def pagination_handler(query: CallbackQuery):
    """Универсальный обработчик пагинации"""
    parts = query.data.split(":")

    if parts[1] == "category":
        # Пагинация категорий
        page = int(parts[2])
        categories = fetch_categories()
        markup = get_categories_keyboard(categories, current_page=page)
        await query.message.edit_text("Выберите категорию товаров:", reply_markup=markup)

    elif parts[1].startswith("product_name"):
        # Пагинация товаров
        cat_id = parts[2]
        page = int(parts[3])

        # Получаем название категории по ID
        category_name = catalog_mapping.get_category_name(cat_id)
        if not category_name:
            await query.answer("Ошибка: категория не найдена")
            return

        conn = create_connection_warehouse()
        try:
            product_names = get_available_product_names(conn, category_name)
            markup = get_product_names_keyboard(product_names, category_name, current_page=page)
            await query.message.edit_text(
                f"Выбрана категория: {category_name}.\nВыберите интересующий вас товар:",
                reply_markup=markup
            )
        finally:
            close_connection_warehouse(conn)

    await query.answer()


@router.callback_query(F.data.startswith("category:"))
async def category_callback_handler(query: CallbackQuery, state: FSMContext):
    cat_id = query.data.split(":")[1]

    # Получаем название категории по ID
    category_name = catalog_mapping.get_category_name(cat_id)
    if not category_name:
        await query.answer("Ошибка: категория не найдена", show_alert=True)
        return

    await state.update_data(selected_category=category_name)
    await state.set_state(CatalogState.browsing_products)

    conn = create_connection_warehouse()
    try:
        product_names = get_available_product_names(conn, category_name)

        if product_names:
            markup = get_product_names_keyboard(product_names, category_name)
            await query.message.edit_text(
                f"Выбрана категория: {category_name}.\nВыберите интересующий вас товар:",
                reply_markup=markup
            )
        else:
            await query.message.edit_text(f"В категории '{category_name}' нет подкатегорий с товарами в наличии.")
    finally:
        close_connection_warehouse(conn)

    await query.answer()


@router.callback_query(F.data.startswith("page:product_name:"))
async def product_name_pagination_handler(query: CallbackQuery):
    """Обработчик пагинации подкатегорий"""
    parts = query.data.split(":")

    # Предполагаем формат "page:product_name:CATEGORY_NAME:PAGE_NUMBER"
    if len(parts) >= 4:
        category_name = parts[2]
        page = int(parts[3])
    else:
        await query.answer("Ошибка формата данных")
        return

    conn = create_connection_warehouse()
    try:
        # Используем функцию из модуля запросов
        product_names = get_available_product_names(conn, category_name)

        markup = get_product_names_keyboard(product_names, category_name, current_page=page)
        await query.message.edit_text(
            f"Выбрана категория: {category_name}.\nВыберите интересующий вас товар::",
            reply_markup=markup
        )
    finally:
        close_connection_warehouse(conn)

    await query.answer()


@router.callback_query(F.data.startswith("product_name:"))
async def show_flavors_handler(query: CallbackQuery, state: FSMContext):
    """Обработчик выбора подкатегории. Отображает список вкусов товаров с общим фото."""
    parts = query.data.split(":")
    cat_id = parts[1]
    prod_id = parts[2]

    # Получаем названия по ID
    category_name = catalog_mapping.get_category_name(cat_id)
    product_info = catalog_mapping.get_product_info(prod_id)

    if not category_name or not product_info:
        await query.answer("Ошибка: данные не найдены", show_alert=True)
        return

    _, product_name = product_info

    # Сохраняем выбранную подкатегорию и другие данные в состоянии
    await state.update_data(
        selected_product_name=product_name,
        original_message_id=query.message.message_id,
        category_name=category_name
    )
    await state.set_state(CatalogState.viewing_product)

    await display_flavors(query, state, category_name, product_name)
    await query.answer()


async def display_flavors(query_or_message, state: FSMContext, category_name: str, product_name: str):
    """Отображает список вкусов для товара"""
    conn = create_connection_warehouse()
    message = query_or_message if isinstance(query_or_message, Message) else query_or_message.message

    try:
        products = get_products_by_category_and_name(conn, category_name, product_name)

        available_products = [p for p in products if p[5] > 0]

        if available_products:
            markup = get_flavors_keyboard(available_products, category_name, product_name)
            flavor_image_path = f"/root/ZK/IMAGES/{category_name}_{product_name}.jpg"
            # flavor_image_path = f"/root/01/IMAGES/{category_name}_{product_name}.jpg"

            # Пытаемся удалить предыдущее фото, если оно было
            data = await state.get_data()
            photo_message_id = data.get("photo_message_id")
            if photo_message_id and isinstance(query_or_message,
                                               CallbackQuery):  # Удаляем только если это результат действия пользователя
                try:
                    await query_or_message.bot.delete_message(message.chat.id, photo_message_id)
                    await state.update_data(photo_message_id=None)  # Сбрасываем ID фото в состоянии
                except TelegramBadRequest as e:
                    logger.warning(f"Не удалось удалить старое фото ({photo_message_id}): {e}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении старого фото ({photo_message_id}): {e}")

            # Отправляем или редактируем сообщение
            if os.path.isfile(flavor_image_path):
                photo = FSInputFile(flavor_image_path)
                try:
                    # Удаляем предыдущее *текстовое* сообщение, если оно было
                    if not photo_message_id:  # Если до этого не было фото
                        await message.delete()
                except Exception as e:
                    logger.warning(f"Не удалось удалить текстовое сообщение перед отправкой фото: {e}")

                new_message = await message.answer_photo(
                    photo=photo,
                    caption=f"Доступные вкусы для {product_name}:",
                    reply_markup=markup
                )
                await state.update_data(photo_message_id=new_message.message_id)
            else:
                # Если фото нет, редактируем исходное сообщение или отправляем новое, если старое было удалено
                try:
                    await message.edit_text(
                        f"Доступные вкусы для {product_name}:",
                        reply_markup=markup
                    )
                except TelegramBadRequest:  # Если сообщение не найдено (например, было фото, которое удалили)
                    await message.answer(
                        f"Доступные вкусы для {product_name}:",
                        reply_markup=markup
                    )

        else:
            await message.edit_text(
                f"Товары в категории '{category_name}', подкатегории '{product_name}' временно отсутствуют."
            )
    finally:
        close_connection_warehouse(conn)


@router.callback_query(F.data.startswith("select_flavor:"))
async def select_flavor_handler(query: CallbackQuery, state: FSMContext):
    """Отображает детали выбранного вкуса и кнопки действий."""
    product_id = int(query.data.split(":")[1])

    await state.update_data(selected_product_id=product_id)

    product_details = get_product_by_id(product_id)
    state_data = await state.get_data()
    category_name = state_data.get("category_name")
    product_name = state_data.get("selected_product_name")

    if product_details and category_name and product_name:
        _, category, _, product_full_name, flavor, price, description, quantity = product_details[
                                                                                  :8]

        text = f"<b>{product_name}</b>\n\n"
        text += f"Выбран вкус: {flavor}\n"
        text += f"Цена: {price} руб.\n"
        if description != "Не добавлено":
            text += f"Описание: {description}\n"

        markup = get_flavor_actions_keyboard(product_id, category_name, product_name)

        photo_message_id = state_data.get("photo_message_id")
        try:
            if photo_message_id:
                await query.bot.edit_message_caption(
                    chat_id=query.message.chat.id,
                    message_id=photo_message_id,
                    caption=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            else:
                await query.message.edit_text(
                    text=text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
        except TelegramBadRequest as e:
            logger.error(f"Ошибка редактирования сообщения при выборе вкуса: {e}")
            await query.message.answer(text, reply_markup=markup, parse_mode="HTML")

    else:
        await query.answer("Ошибка: Товар не найден или данные состояния потеряны.", show_alert=True)

    await query.answer()


@router.callback_query(F.data.startswith("flavor_action:add_cart:"))
async def add_selected_flavor_to_cart(query: CallbackQuery):
    """Добавляет выбранный вкус в корзину."""
    product_id = int(query.data.split(":")[2])
    user_id = query.from_user.id

    # Добавляем товар в корзину
    result = add_to_cart(user_id, product_id, 1)  # По умолчанию 1 шт

    if result == 'added':
        await query.answer(text='✅ Товар успешно добавлен в корзину!', show_alert=True)
    elif result == 'exists':
        await query.answer(text='⚠️ Этот товар уже находится в корзине.', show_alert=True)
    else: # result is False or None
        await query.answer(text='❌ Не удалось добавить товар в корзину!', show_alert=True)


@router.callback_query(F.data.startswith("flavor_action:add_fav:"))
async def add_selected_flavor_to_favorites(query: CallbackQuery):
    """Добавляет выбранный вкус в избранное."""
    product_id = int(query.data.split(":")[2])
    user_id = query.from_user.id

    is_favorite = await asyncio.to_thread(favorites_db.is_product_in_favorites, user_id, product_id)

    if is_favorite:
        await query.answer(text='Этот товар уже есть в вашем списке избранного!', show_alert=True)
    else:
        result = add_product_to_favorites(user_id, product_id)

        if result:
            await query.answer(text='❤️ Товар успешно добавлен в избранное!', show_alert=True)
        else:
            await query.answer(text='❌ Не удалось добавить товар в избранное!', show_alert=True)


@router.callback_query(F.data.startswith("flavor_action:back_flavors:"))
async def back_to_flavors_selection(query: CallbackQuery, state: FSMContext):
    """Возвращает пользователя к списку вкусов для текущего товара."""
    _, _, cat_id, prod_id = query.data.split(":")

    # Получаем названия по ID
    category_name = catalog_mapping.get_category_name(cat_id)
    product_info = catalog_mapping.get_product_info(prod_id)

    if not category_name or not product_info:
        await query.answer("Ошибка: данные не найдены", show_alert=True)
        return

    _, product_name = product_info

    await display_flavors(query, state, category_name, product_name)
    await query.answer()


@router.callback_query(F.data.startswith("product_nav:"))
async def product_navigation_handler(query: CallbackQuery):
    """Обработчик навигации по списку товаров"""
    _, cat_id, prod_id, idx = query.data.split(":")
    idx = int(idx)

    # Получаем названия по ID
    category_name = catalog_mapping.get_category_name(cat_id)
    product_info = catalog_mapping.get_product_info(prod_id)

    if not category_name or not product_info:
        await query.answer("Ошибка: данные не найдены", show_alert=True)
        return

    _, product_name = product_info

    all_products = fetch_products_by_category_and_product_name(category_name, product_name)

    # Фильтруем товары, у которых количество > 0
    products = [product for product in all_products if product[5] > 0]

    if products and 0 <= idx < len(products):
        await show_product_details(query.message, products, idx, category_name, product_name)
    await query.answer()


@router.callback_query(F.data.startswith("back_to_products:"))
async def back_to_products_handler(query: CallbackQuery, state: FSMContext):
    """Обработчик возврата к списку товаров"""
    _, cat_id, prod_id = query.data.split(":")

    # Получаем названия по ID
    category_name = catalog_mapping.get_category_name(cat_id)
    if not category_name:
        await query.answer("Ошибка: категория не найдена", show_alert=True)
        return

    await state.set_state(CatalogState.browsing_products)

    # Получаем данные состояния
    data = await state.get_data()
    photo_message_id = data.get("photo_message_id")
    original_message_id = data.get("original_message_id")

    # Если было отправлено фото, удаляем это сообщение
    if photo_message_id:
        try:
            await query.bot.delete_message(
                chat_id=query.message.chat.id,
                message_id=photo_message_id
            )
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения с фото: {e}")

    # Получаем список товаров для отображения
    conn = create_connection_warehouse()
    try:
        product_names = get_available_product_names(conn, category_name)

        if product_names:
            markup = get_product_names_keyboard(product_names, category_name)

            # Если запрос пришел из сообщения с фото
            if query.message.message_id == photo_message_id:
                try:
                    await query.bot.edit_message_text(
                        chat_id=query.message.chat.id,
                        message_id=original_message_id,
                        text=f"Выбрана категория: {category_name}.\nВыберите интересующий вас товар:",
                        reply_markup=markup
                    )
                    await query.answer()
                    return
                except Exception as e:
                    logger.error(f"Ошибка при редактировании исходного сообщения: {e}")

            await query.message.edit_text(
                f"Выбрана категория: {category_name}.\nВыберите интересующий вас товар:",
                reply_markup=markup
            )
        else:
            await query.message.edit_text(f"В категории '{category_name}' нет доступных товаров.")
    finally:
        close_connection_warehouse(conn)

    await query.answer()


@router.callback_query(F.data == "cancel_catalog")
async def cancel_catalog_callback_handler(query: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Отмена' в меню категорий. Возврат в главное меню."""
    # Получаем данные перед очисткой состояния
    data = await state.get_data()
    photo_message_id = data.get("photo_message_id")

    # Очищаем состояние
    await state.clear()

    # Если есть сообщение с фото, удаляем его
    if photo_message_id:
        try:
            # Проверяем, откуда пришел запрос
            if query.message.message_id == photo_message_id:
                # Если запрос из сообщения с фото, отправляем новое сообщение
                await query.message.delete()
                await query.message.answer("Вы вернулись в главное меню.")
                await query.message.answer("Выберите раздел:", reply_markup=main_menu_keyboard)
                await query.answer()
                return
            else:
                # Пытаемся удалить сообщение с фото
                await query.bot.delete_message(
                    chat_id=query.message.chat.id,
                    message_id=photo_message_id
                )
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения с фото: {e}")

    # Стандартное поведение - редактируем текущее сообщение
    try:
        await query.message.edit_text("Вы вернулись в главное меню.", reply_markup=None)
        await query.message.answer("Выберите раздел:", reply_markup=main_menu_keyboard)
    except Exception as e:
        # В случае ошибки редактирования (например, сообщение уже удалено)
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await query.message.answer("Вы вернулись в главное меню.")
        await query.message.answer("Выберите раздел:", reply_markup=main_menu_keyboard)

    await query.answer()


@router.callback_query(F.data == "cancel_category_selection")
async def cancel_category_selection_callback_handler(query: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Отмена' в меню подкатегорий. Возврат к выбору категорий."""
    # Получаем данные состояния
    data = await state.get_data()
    photo_message_id = data.get("photo_message_id")

    # Обновляем состояние
    await state.set_state(CatalogState.browsing_categories)

    # Если есть сообщение с фото, удаляем его
    if photo_message_id:
        try:
            # Проверяем, откуда пришел запрос
            if query.message.message_id == photo_message_id:
                # Если запрос из сообщения с фото, отправляем новое сообщение
                await query.message.delete()

                # Получаем категории и отправляем новое сообщение
                categories = fetch_categories()
                if categories:
                    markup = get_categories_keyboard(categories)
                    await query.message.answer("Выберите категорию товаров:", reply_markup=markup)
                else:
                    await query.message.answer("К сожалению, каталог товаров пуст.")

                await query.answer()
                return
            else:
                # Пытаемся удалить сообщение с фото
                await query.bot.delete_message(
                    chat_id=query.message.chat.id,
                    message_id=photo_message_id
                )
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения с фото: {e}")

    # Стандартное поведение
    categories = fetch_categories()
    if categories:
        markup = get_categories_keyboard(categories)
        await query.message.edit_text("Выберите категорию товаров:", reply_markup=markup)
    else:
        await query.message.edit_text("К сожалению, каталог товаров пуст.")

    await query.answer()


async def show_product_details(message, products, idx, category_name, product_name):
    """Отображает детальную информацию о товаре"""
    if not products or idx >= len(products):
        await message.edit_text("Товар не найден.")
        return

    product = products[idx]
    product_full_name, flavor, price, product_id, description, quantity, image_path = product

    product_text = (
        f"<b>{product_full_name}</b>\n\n"
        f"<b>вкус:</b> {flavor}\n"
        f"<b>Цена:</b> {price} руб.\n"
        f"<b>Описание:</b>\n{description or 'Описание отсутствует'}"
    )

    markup = get_product_details_keyboard(
        product_id,
        category_name,
        product_name,
        current_idx=idx,
        total_products=len(products)
    )

    try:
        image_path = 'C:\\Users\\Iskander\\PycharmProjects\\ZK\\database\\users\\' + image_path
        if image_path and os.path.isfile(image_path):
            photo = FSInputFile(image_path)
            if hasattr(message, 'message_id'):
                await message.answer_photo(photo=photo, caption=product_text, reply_markup=markup, parse_mode="HTML")
            else:
                await message.delete()
                await message.answer_photo(photo=photo, caption=product_text, reply_markup=markup, parse_mode="HTML")
        else:
            logger.info(f"Image not found: {image_path}, exists: {os.path.isfile(image_path) if image_path else False}")
            if hasattr(message, 'edit_text'):
                await message.edit_text(product_text, reply_markup=markup, parse_mode="HTML")
            else:
                await message.answer(product_text, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        logger.info(f"Error displaying product: {e}")
        await message.answer(f"Ошибка при отображении товара: {e}")
