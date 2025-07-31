import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.users.favorites_db import (
    get_user_favorites,
    add_product_to_favorites,
    remove_product_from_favorites
)
from database.users.warehouse_connection import create_connection_warehouse, close_connection_warehouse
from keyboards.users.favorites_keyboards import (
    get_empty_favorites_keyboard,
    get_favorites_keyboard,
)
from keyboards.users.profile_keyboards import get_profile_keyboard
from states.favorites_state import FavoritesState
from database.users.database import add_to_cart

router = Router()


def fetch_categories():
    """Получение всех доступных категорий со склада"""
    conn = create_connection_warehouse()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT DISTINCT category 
        FROM products 
        WHERE is_active = 1 AND quantity > 0
        ORDER BY category
        ''')

        categories = [row[0] for row in cursor.fetchall()]
        return categories
    finally:
        close_connection_warehouse(conn)


@router.callback_query(F.data == "profile:favorites")
async def show_favorites(callback: CallbackQuery, state: FSMContext):
    """Показать избранное пользователя или сообщение о пустом списке"""
    await state.set_state(FavoritesState.viewing_favorites)

    telegram_id = callback.from_user.id
    favorites = get_user_favorites(telegram_id)

    if favorites:
        # Показываем первый товар в избранном
        await show_favorite_item(callback.message, telegram_id, 0)
    else:
        await callback.message.edit_text(
            "У вас пока нет товаров в избранном. Вы можете добавить товары из каталога!",
            reply_markup=get_empty_favorites_keyboard()
        )

    await callback.answer()


async def show_favorite_item(message, telegram_id, index):
    """Показать конкретный товар из избранного по индексу"""
    favorites = get_user_favorites(telegram_id)

    if not favorites or index >= len(favorites):
        await message.edit_text(
            "У вас пока нет товаров в избранном. Вы можете добавить товары из каталога!",
            reply_markup=get_empty_favorites_keyboard()
        )
        return

    product = favorites[index]
    category = product[1]
    product_name = product[2]
    product_full_name = product[3]
    flavor = product[4]
    price = product[5]
    description = product[6]
    quantity = product[7]

    product_info = (
        f"<b>{product_full_name}</b>\n\n"
        f"<b>Категория:</b> {category}\n"
        f"<b>Вкус:</b> {flavor}\n"
        f"<b>Цена:</b> {price} ₽\n"
        f"<b>В наличии:</b> {quantity} шт.\n\n"
    )

    if description != "Не добавлено":
        product_info += "{description}\n\n"

    markup = get_favorites_keyboard(favorites, index)

    image_path = f"C:\\Users\\Iskander\\PycharmProjects\\ZK\\IMAGES\\{category}_{product_name}.jpg"

    if os.path.isfile(image_path):
        photo = FSInputFile(image_path)
        await message.delete()
        await message.answer_photo(
            photo=photo,
            caption=product_info,
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        await message.edit_text(
            product_info,
            reply_markup=markup,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("favorites:next:"))
async def navigate_favorites_next(callback: CallbackQuery):
    """Перейти к следующему товару в избранном"""
    current_index = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id

    await show_favorite_item(callback.message, telegram_id, current_index + 1)
    await callback.answer()


@router.callback_query(F.data.startswith("favorites:prev:"))
async def navigate_favorites_prev(callback: CallbackQuery):
    """Перейти к предыдущему товару в избранном"""
    current_index = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id

    await show_favorite_item(callback.message, telegram_id, current_index - 1)
    await callback.answer()


@router.callback_query(F.data.startswith("favorites:add_to_cart:"))
async def add_favorite_to_cart(callback: CallbackQuery):
    """Добавить товар из избранного в корзину"""
    product_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = add_to_cart(user_id, product_id, 1)  # По умолчанию добавляем 1 единицу товара

    if result:
        await callback.answer(
            text="✅ Товар успешно добавлен в корзину!",
            show_alert=True
        )
    else:
        await callback.answer(
            text="❌ Не удалось добавить товар в корзину!",
            show_alert=True
        )


@router.callback_query(F.data.startswith("favorites:remove:"))
async def remove_from_favorites(callback: CallbackQuery):
    """Удалить товар из избранного"""
    product_id = int(callback.data.split(":")[2])
    telegram_id = callback.from_user.id

    # Получаем текущий список избранного
    favorites = get_user_favorites(telegram_id)

    # Находим индекс удаляемого товара
    current_index = None
    for i, item in enumerate(favorites):
        if item[0] == product_id:  # product_id - первый элемент в кортеже
            current_index = i
            break

    # Удаляем товар
    result = remove_product_from_favorites(telegram_id, product_id)

    if result:
        await callback.answer(
            text="✔️ Товар удален из избранного!",
            show_alert=True
        )

        # Получаем обновленный список избранного
        new_favorites = get_user_favorites(telegram_id)

        if not new_favorites:
            # Если после удаления список пустой
            await callback.message.edit_text(
                "У вас пока нет товаров в избранном. Вы можете добавить товары из каталога!",
                reply_markup=get_empty_favorites_keyboard()
            )
        else:
            # Определяем, какой индекс показать
            if current_index is not None:
                # Если был удален последний элемент, показываем предыдущий
                if current_index >= len(new_favorites):
                    new_index = max(0, current_index - 1)
                else:
                    # Иначе показываем товар с тем же индексом (который теперь будет следующий)
                    new_index = current_index

                await show_favorite_item(callback.message, telegram_id, new_index)
            else:
                # Если по какой-то причине мы не смогли найти индекс
                await show_favorite_item(callback.message, telegram_id, 0)
    else:
        await callback.answer(
            text="❌ Не удалось удалить товар из избранного!",
            show_alert=True
        )


@router.callback_query(F.data == "favorites:back_to_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться назад в профиль"""
    await state.clear()

    try:
        await callback.message.edit_text(
            "Профиль:",
            reply_markup=get_profile_keyboard()
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(
            "Профиль:",
            reply_markup=get_profile_keyboard()
        )

    await callback.answer()


@router.callback_query(F.data.startswith("favorites_catalog:add:"))
async def add_to_favorites_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления товара в избранное"""
    product_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = add_product_to_favorites(user_id, product_id)

    if result:
        await callback.answer(
            text="✅ Товар успешно добавлен в избранное!",
            show_alert=True
        )

        # Предложение продолжить или вернуться в избранное
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="📋 Вернуться к списку избранного",
            callback_data="favorites_catalog:back_to_favorites"
        ))
        builder.row(InlineKeyboardButton(
            text="🔍 Продолжить выбор товаров",
            callback_data=f"favorites_catalog:back_to_products:{(await state.get_data())['selected_category']}"
        ))

        # Определяем, нужно ли редактировать сообщение с фото или обычное сообщение
        state_data = await state.get_data()
        if 'photo_message_id' in state_data:
            # Не можем редактировать фото, отправляем новое сообщение
            await callback.message.answer(
                "Товар добавлен в избранное! Что дальше?",
                reply_markup=builder.as_markup()
            )
        else:
            await callback.message.edit_text(
                "Товар добавлен в избранное! Что дальше?",
                reply_markup=builder.as_markup()
            )
    else:
        await callback.answer(
            text="❌ Не удалось добавить товар в избранное!",
            show_alert=True
        )


@router.callback_query(F.data == "favorites_catalog:back_to_favorites")
async def back_to_favorites_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата в список избранного из каталога"""
    await show_favorites(callback, state)


@router.callback_query(F.data == "favorites:noop")
async def favorites_noop_callback(callback: CallbackQuery):
    """Handles clicks on inactive navigation buttons."""
    await callback.answer(cache_time=5)
