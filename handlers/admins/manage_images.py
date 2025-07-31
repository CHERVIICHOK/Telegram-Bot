import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from filters.admin_filter import AdminFilter, CouriersFilter
from keyboards.users.keyboards import main_menu_keyboard
from states.product_image_state import ProductImageState
from keyboards.admins.image_keyboards import (
    get_image_categories_keyboard,
    get_image_product_names_keyboard
)
from keyboards.admins.menu_keyboard import get_admin_menu_keyboard, get_courier_menu_keyboard
from database.admins.image_db import (
    get_categories,
    get_product_names_by_category,
    get_product_image_by_name,
    add_or_update_product_image
)

import logging

logger = logging.getLogger(__name__)

router = Router()

courier_router = Router()
courier_router.message.filter(CouriersFilter())
courier_router.callback_query.filter(CouriersFilter())

admin_router = Router()
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

router.include_router(courier_router)
router.include_router(admin_router)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/webp']
IMAGES_DIR = "IMAGES"


# Начало процесса добавления изображения
@router.callback_query(F.data == "add_product_image", StateFilter(default_state))
async def start_add_image(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала процесса добавления изображения"""
    categories = get_categories()

    if not categories:
        await callback.message.answer("Не найдены категории товаров. Сначала добавьте товары.")
        return

    await callback.message.answer(
        "Выберите категорию товара:",
        reply_markup=get_image_categories_keyboard(categories)
    )
    await state.set_state(ProductImageState.select_category)
    await callback.answer()


# Обработка выбора категории
@router.callback_query(StateFilter(ProductImageState.select_category), F.data.startswith("img_category:"))
async def category_selected(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории товара"""
    category = callback.data.split(":")[1]

    await state.update_data(category=category)

    product_names = get_product_names_by_category(category)

    if not product_names:
        await callback.message.answer(
            f"В категории '{category}' нет товаров. Вернитесь и выберите другую категорию.",
            reply_markup=get_image_categories_keyboard(get_categories())
        )
        return

    await callback.message.answer(
        f"Выберите название товара из категории '{category}':",
        reply_markup=get_image_product_names_keyboard(product_names, category)
    )
    await state.set_state(ProductImageState.select_product)
    await callback.answer()


# Обработка выбора продукта
@router.callback_query(StateFilter(ProductImageState.select_product), F.data.startswith("img_product:"))
async def product_selected(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора названия продукта"""
    product_name = callback.data.split(":")[1]

    await state.update_data(product_name=product_name)

    existing_image = get_product_image_by_name(product_name)

    if existing_image:
        message_text = (f"Для товара '{product_name}' уже загружено изображение.\n"
                        f"Вы можете заменить его, отправив новое.")
    else:
        message_text = f"Отправьте изображение для товара '{product_name}'."

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_upload")]
    ])

    await callback.message.answer(message_text, reply_markup=cancel_kb)
    await state.set_state(ProductImageState.upload_image)
    await callback.answer()


# Обработка пагинации для категорий
@router.callback_query(F.data.startswith("img_page:img_category:"))
async def handle_category_pagination(callback: CallbackQuery):
    """Обработчик пагинации при выборе категорий"""
    page = int(callback.data.split(":")[-1])
    categories = get_categories()

    await callback.message.edit_reply_markup(
        reply_markup=get_image_categories_keyboard(categories, current_page=page)
    )
    await callback.answer()


# Обработка пагинации для товаров
@router.callback_query(F.data.startswith("img_page:img_product:"))
async def handle_product_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработчик пагинации при выборе товаров"""
    page = int(callback.data.split(":")[-1])

    user_data = await state.get_data()
    category = user_data.get("category")

    product_names = get_product_names_by_category(category)

    await callback.message.edit_reply_markup(
        reply_markup=get_image_product_names_keyboard(product_names, category, current_page=page)
    )
    await callback.answer()


# Обработчик кнопки "Назад" при выборе категории
@router.callback_query(F.data == "cancel_image_upload")
async def cancel_image_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены выбора категории"""
    is_admin = await AdminFilter().__call__(callback)
    is_courier = await CouriersFilter().__call__(callback)

    await state.clear()

    if is_admin:
        menu_keyboard = get_admin_menu_keyboard()
        menu_text = "администратора"
    elif is_courier:
        menu_keyboard = get_courier_menu_keyboard()
        menu_text = "курьера"
    else:
        menu_keyboard = main_menu_keyboard()
        menu_text = ""

    await callback.message.edit_text(
        f"Процесс добавления изображения отменен. Вы вернулись в главное меню {menu_text}:",
        reply_markup=menu_keyboard
    )

    await callback.answer()


# Обработчик кнопки "Назад" при выборе товара
@router.callback_query(F.data == "back_to_image_categories")
async def back_to_image_categories(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору категории"""
    await state.set_state(ProductImageState.select_category)
    categories = get_categories()

    await callback.message.answer(
        "Выберите категорию товара:",
        reply_markup=get_image_categories_keyboard(categories)
    )
    await callback.answer()


# Обработка загрузки изображения через фото
@router.message(StateFilter(ProductImageState.upload_image), F.photo)
async def process_image_upload(message: Message, state: FSMContext, bot):
    """Обработчик загрузки изображения через фото"""
    user_data = await state.get_data()
    category = user_data.get("category")
    product_name = user_data.get("product_name")

    photo = message.photo[-1]

    if photo.file_size > MAX_FILE_SIZE:
        await message.answer(
            f"Размер изображения превышает допустимый лимит (5 МБ). Отправьте файл меньшего размера."
        )
        return

    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    # ГЕНЕРИРУЕМ ИМЯ ФАЙЛА
    file_name = f"{category}_{product_name}.jpg"
    file_path = os.path.join(IMAGES_DIR, file_name)
    absolute_path = os.path.abspath(file_path)

    try:
        file_info = await bot.get_file(photo.file_id)
        await bot.download_file(file_info.file_path, file_path)

        if add_or_update_product_image(
                product_name,
                absolute_path,
                category,
                photo.file_size,
                "image/jpeg"
        ):
            is_admin = await AdminFilter().__call__(message)
            is_courier = await CouriersFilter().__call__(message)

            if is_admin:
                menu_keyboard = get_admin_menu_keyboard()
                menu_text = "администратора"
            elif is_courier:
                menu_keyboard = get_courier_menu_keyboard()
                menu_text = "курьера"
            else:
                menu_keyboard = main_menu_keyboard()
                menu_text = ""

            await message.answer(
                f"✅ Изображение для товара '{product_name}' успешно сохранено!\n\nВы вернулись в главное меню {menu_text}:",
                reply_markup=menu_keyboard
            )

        else:
            await message.answer("Произошла ошибка при сохранении данных в базу.")

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {e}")
        await message.answer(
            "Произошла ошибка при сохранении изображения. Пожалуйста, попробуйте снова."
        )


# Обработка загрузки изображения через документ
@router.message(StateFilter(ProductImageState.upload_image), F.document)
async def process_document_upload(message: Message, state: FSMContext, bot):
    """Обработчик загрузки изображения через документ"""
    user_data = await state.get_data()
    category = user_data.get("category")
    product_name = user_data.get("product_name")

    if message.document.mime_type not in ALLOWED_CONTENT_TYPES:
        await message.answer(
            "Пожалуйста, отправьте изображение в формате JPEG, PNG или WebP."
        )
        return

    if message.document.file_size > MAX_FILE_SIZE:
        await message.answer(
            f"Размер изображения превышает допустимый лимит (5 МБ). Отправьте файл меньшего размера."
        )
        return

    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    extension = message.document.mime_type.split("/")[1]
    if extension == "jpeg":
        extension = "jpg"

    # ГЕНЕРИРУЕМ ИМЯ ФАЙЛА
    file_name = f"{category}_{product_name}.{extension}"
    file_path = os.path.join(IMAGES_DIR, file_name)
    absolute_path = os.path.abspath(file_path)

    is_admin = await AdminFilter().__call__(message)
    is_courier = await CouriersFilter().__call__(message)

    if is_admin:
        menu_keyboard = get_admin_menu_keyboard()
        menu_text = "администратора"
    elif is_courier:
        menu_keyboard = get_courier_menu_keyboard()
        menu_text = "курьера"
    else:
        menu_keyboard = main_menu_keyboard()
        menu_text = ""

    try:
        file_info = await bot.get_file(message.document.file_id)
        await bot.download_file(file_info.file_path, file_path)

        if add_or_update_product_image(
                product_name,
                absolute_path,
                category,
                message.document.file_size,
                message.document.mime_type
        ):
            await message.answer(
                f"✅ Изображение для товара '{product_name}' успешно сохранено!\nВы вернулись в главное меню {menu_text}",
                reply_markup=menu_keyboard
            )
        else:
            await message.answer("Произошла ошибка при сохранении данных в базу.",
                                 reply_markup=menu_keyboard
                                 )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {e}")
        await message.answer(
            "Произошла ошибка при сохранении изображения. Пожалуйста, попробуйте снова.",
            reply_markup=menu_keyboard
        )


# Обработка неверного формата файла
@router.message(StateFilter(ProductImageState.upload_image))
async def wrong_input(message: Message):
    """Обработчик неверного ввода на этапе загрузки изображения"""
    await message.answer(
        "Пожалуйста, отправьте изображение в формате фото или документа (JPEG, PNG, WebP)."
    )


# Обработчик кнопки отмены
@router.callback_query(F.data == "cancel_upload")
async def cancel_upload(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены процесса загрузки"""
    is_admin = await AdminFilter().__call__(callback)
    is_courier = await CouriersFilter().__call__(callback)

    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    if is_admin:
        menu_keyboard = get_admin_menu_keyboard()
        menu_text = "администратора"
    elif is_courier:
        menu_keyboard = get_courier_menu_keyboard()
        menu_text = "курьера"
    else:
        menu_keyboard = main_menu_keyboard()
        menu_text = ""

    await callback.message.edit_text(
        f"Процесс добавления изображения отменен. Вы вернулись в главное меню {menu_text}:",
        reply_markup=menu_keyboard
    )

    await callback.answer()


# Обработчик кнопки "noop"
@router.callback_query(F.data == "img_noop")
async def handle_noop(callback: CallbackQuery):
    """Обработчик пустой кнопки"""
    await callback.answer()
