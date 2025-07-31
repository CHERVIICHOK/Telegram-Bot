from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.admins.products_db import (
    get_paginated_products, get_product_details, add_product,
    update_product, toggle_product_status, get_categories,
    add_category, update_category, delete_category, ensure_product_status_column
)
from filters.admin_filter import AdminFilter
from keyboards.admins.product_keyboards import (
    get_products_menu_keyboard, get_category_selection_keyboard,
    get_products_list_keyboard, get_product_details_keyboard,
    get_edit_product_keyboard, get_categories_management_keyboard,
    get_confirm_cancel_keyboard, get_back_keyboard
)
from utils.product_utils import (
    format_product_details, validate_product_data,
    prepare_product_data, get_field_description
)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

# Состояния для FSM
class ProductStates(StatesGroup):
    choosing_category = State()
    entering_product_name = State()
    entering_flavor = State()
    entering_price = State()
    entering_description = State()
    entering_quantity = State()
    entering_image_path = State()

    editing_product = State()
    editing_field = State()

    adding_category = State()
    editing_category = State()
    confirming_category_delete = State()


# Глобальные переменные для хранения состояния между вызовами
CURRENT_CATEGORY = {}  # user_id -> category
CURRENT_PAGE = {}  # user_id -> page
CURRENT_PRODUCT = {}  # user_id -> product_id
TEMP_PRODUCT_DATA = {}  # user_id -> dict

# Убедимся, что столбец is_active существует
ensure_product_status_column()


# Обработчики команд
@router.callback_query(F.data == "manage_products")
async def cmd_manage_products(callback: CallbackQuery):
    """Обработчик для кнопки управления товарами"""
    await callback.message.edit_text(
        "🛍️ <b>Управление товарами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_products_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_admin_menu")
async def cmd_back_to_admin_menu(callback: CallbackQuery):
    """Обработчик для возврата в главное меню админа"""
    from keyboards.admins.menu_keyboard import get_admin_menu_keyboard

    await callback.message.edit_text(
        "🔑 <b>Панель администратора</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_products_menu")
async def cmd_back_to_products_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик для возврата в меню управления товарами"""
    await state.clear()
    await cmd_manage_products(callback)


# Просмотр товаров
@router.callback_query(F.data == "view_products")
async def cmd_view_products(callback: CallbackQuery):
    """Обработчик для просмотра товаров (выбор категории)"""
    user_id = callback.from_user.id
    CURRENT_PAGE[user_id] = 1

    categories = get_categories()

    await callback.message.edit_text(
        "🗂 <b>Выберите категорию товаров:</b>",
        reply_markup=get_category_selection_keyboard(categories, action="view"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_category:"))
async def cmd_view_category(callback: CallbackQuery):
    """Обработчик для просмотра товаров в выбранной категории"""
    user_id = callback.from_user.id
    _, category, page_str = callback.data.split(":", 2)
    page = int(page_str) if page_str.isdigit() else 1

    CURRENT_PAGE[user_id] = page
    CURRENT_CATEGORY[user_id] = None if category == "all" else category

    await show_products_list(callback.message, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("products_page:"))
async def cmd_products_page(callback: CallbackQuery):
    """Обработчик для пагинации списка товаров"""
    user_id = callback.from_user.id
    data_parts = callback.data.split(":", 2)

    page = int(data_parts[1])
    category = None if data_parts[2] == "all" else data_parts[2]

    CURRENT_PAGE[user_id] = page
    CURRENT_CATEGORY[user_id] = category

    await show_products_list(callback.message, user_id)
    await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def cmd_back_to_categories(callback: CallbackQuery):
    """Обработчик для возврата к выбору категории"""
    await cmd_view_products(callback)


@router.callback_query(F.data.startswith("product_details:"))
async def cmd_product_details(callback: CallbackQuery):
    """Обработчик для просмотра деталей товара"""
    user_id = callback.from_user.id
    _, product_id = callback.data.split(":", 1)

    CURRENT_PRODUCT[user_id] = int(product_id)

    product = get_product_details(int(product_id))
    if not product:
        await callback.message.edit_text(
            "❌ Товар не найден",
            reply_markup=get_back_keyboard("back_to_products_list")
        )
        await callback.answer()
        return

    is_active = product[9] if len(product) > 9 else 1

    await callback.message.edit_text(
        format_product_details(product),
        reply_markup=get_product_details_keyboard(product_id, is_active=bool(is_active)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_products_list")
async def cmd_back_to_products_list(callback: CallbackQuery):
    """Обработчик для возврата к списку товаров"""
    user_id = callback.from_user.id
    await show_products_list(callback.message, user_id)
    await callback.answer()


# Добавление товара
@router.callback_query(F.data == "add_product")
async def cmd_add_product(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала процесса добавления товара"""
    user_id = callback.from_user.id
    TEMP_PRODUCT_DATA[user_id] = {}

    categories = get_categories()

    await callback.message.edit_text(
        "🗂 <b>Выберите категорию для нового товара или введите новую:</b>",
        reply_markup=get_category_selection_keyboard(categories, action="add"),
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.choosing_category)
    await callback.answer()


@router.callback_query(F.data.startswith("select_category:"), ProductStates.choosing_category)
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории при добавлении товара"""
    user_id = callback.from_user.id
    _, category = callback.data.split(":", 1)

    TEMP_PRODUCT_DATA[user_id]['category'] = category

    await callback.message.edit_text(
        "📝 <b>Введите название товара:</b>"
    )

    await state.set_state(ProductStates.entering_product_name)
    await callback.answer()


@router.message(ProductStates.choosing_category)
async def process_category_input(message: Message, state: FSMContext):
    """Обработчик ввода новой категории при добавлении товара"""
    user_id = message.from_user.id
    category = message.text.strip()

    if not category:
        await message.answer("❌ Категория не может быть пустой. Попробуйте еще раз:")
        return

    TEMP_PRODUCT_DATA[user_id]['category'] = category

    await message.answer(
        "📝 <b>Введите название товара:</b>",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.entering_product_name)


@router.message(ProductStates.entering_product_name)
async def process_product_name(message: Message, state: FSMContext):
    """Обработчик ввода названия товара"""
    user_id = message.from_user.id
    product_name = message.text.strip()

    if not product_name:
        await message.answer("❌ Название товара не может быть пустым. Попробуйте еще раз:")
        return

    TEMP_PRODUCT_DATA[user_id]['product_name'] = product_name

    await message.answer(
        "🍬 <b>Введите Вкус товара (если есть):</b>\n"
        "Если у товара нет Вкуса, просто отправьте '-'",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.entering_flavor)


@router.message(ProductStates.entering_flavor)
async def process_flavor(message: Message, state: FSMContext):
    """Обработчик ввода Вкуса товара"""
    user_id = message.from_user.id
    flavor = message.text.strip()

    if flavor == '-':
        flavor = ''

    TEMP_PRODUCT_DATA[user_id]['flavor'] = flavor

    # Формируем полное название товара
    product_name = TEMP_PRODUCT_DATA[user_id]['product_name']
    if flavor:
        TEMP_PRODUCT_DATA[user_id]['product_full_name'] = f"{product_name} {flavor}"
    else:
        TEMP_PRODUCT_DATA[user_id]['product_full_name'] = product_name

    await message.answer(
        "💰 <b>Введите цену товара (в рублях):</b>",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.entering_price)


@router.message(ProductStates.entering_price)
async def process_price(message: Message, state: FSMContext):
    """Обработчик ввода цены товара"""
    user_id = message.from_user.id
    price_text = message.text.strip()

    try:
        price = float(price_text)
        if price < 0:
            raise ValueError("Negative price")
    except ValueError:
        await message.answer("❌ Введите корректную цену (положительное число). Попробуйте еще раз:")
        return

    TEMP_PRODUCT_DATA[user_id]['price'] = price

    await message.answer(
        "📋 <b>Введите описание товара:</b>\n"
        "Если хотите пропустить этот шаг, просто отправьте '-'",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.entering_description)


@router.message(ProductStates.entering_description)
async def process_description(message: Message, state: FSMContext):
    """Обработчик ввода описания товара"""
    user_id = message.from_user.id
    description = message.text.strip()

    if description == '-':
        description = ''

    TEMP_PRODUCT_DATA[user_id]['description'] = description

    await message.answer(
        "🔢 <b>Введите количество товара на складе:</b>",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.entering_quantity)


@router.message(ProductStates.entering_quantity)
async def process_quantity(message: Message, state: FSMContext):
    """Обработчик ввода количества товара"""
    user_id = message.from_user.id
    quantity_text = message.text.strip()

    try:
        quantity = int(quantity_text)
        if quantity < 0:
            raise ValueError("Negative quantity")
    except ValueError:
        await message.answer("❌ Введите корректное количество (целое неотрицательное число). Попробуйте еще раз:")
        return

    TEMP_PRODUCT_DATA[user_id]['quantity'] = quantity

    await message.answer(
        "🖼 <b>Введите путь к изображению товара:</b>\n"
        "Если хотите пропустить этот шаг, просто отправьте '-'",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.entering_image_path)


@router.message(ProductStates.entering_image_path)
async def process_image_path(message: Message, state: FSMContext):
    """Обработчик ввода пути к изображению товара"""
    user_id = message.from_user.id
    image_path = message.text.strip()

    if image_path == '-':
        image_path = ''

    TEMP_PRODUCT_DATA[user_id]['image_path'] = image_path
    TEMP_PRODUCT_DATA[user_id]['is_active'] = 1  # По умолчанию товар активен

    # Добавляем товар в базу данных
    product_id = add_product(TEMP_PRODUCT_DATA[user_id])

    if product_id != -1:
        product = get_product_details(product_id)

        await message.answer(
            "✅ <b>Товар успешно добавлен!</b>\n\n" +
            format_product_details(product),
            reply_markup=get_products_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при добавлении товара!</b>\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=get_products_menu_keyboard(),
            parse_mode="HTML"
        )

    # Очищаем временные данные и состояние
    TEMP_PRODUCT_DATA.pop(user_id, None)
    await state.clear()


# Редактирование товара
@router.callback_query(F.data.startswith("edit_product:"))
async def cmd_edit_product(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала процесса редактирования товара"""
    _, product_id = callback.data.split(":", 1)

    await callback.message.edit_text(
        "✏️ <b>Выберите, что хотите изменить:</b>",
        reply_markup=get_edit_product_keyboard(product_id),
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.editing_product)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_product_field:"), ProductStates.editing_product)
async def cmd_edit_product_field(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора поля для редактирования"""
    user_id = callback.from_user.id
    _, product_id, field = callback.data.split(":", 2)

    # Сохраняем ID товара и поле для редактирования
    await state.update_data(product_id=int(product_id), field=field)

    # Получаем текущее значение поля
    product = get_product_details(int(product_id))
    field_value = ""

    if product:
        if field == "category":
            field_value = product[1]
        elif field == "product_name":
            field_value = product[2]
        elif field == "flavor":
            field_value = product[4]
        elif field == "price":
            field_value = product[5]
        elif field == "description":
            field_value = product[6]
        elif field == "quantity":
            field_value = product[7]
        elif field == "image_path":
            field_value = product[8]

    field_description = get_field_description(field)

    await callback.message.edit_text(
        f"✏️ <b>Редактирование: {field_description}</b>\n\n"
        f"Текущее значение: <b>{field_value}</b>\n\n"
        f"Введите новое значение:",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.editing_field)
    await callback.answer()


@router.message(ProductStates.editing_field)
async def process_field_edit(message: Message, state: FSMContext):
    """Обработчик ввода нового значения для поля товара"""
    user_id = message.from_user.id
    new_value = message.text.strip()

    # Получаем сохраненные данные
    data = await state.get_data()
    product_id = data.get('product_id')
    field = data.get('field')

    # Проверяем валидность введенных данных
    is_valid, error_message = validate_product_data(field, new_value)

    if not is_valid:
        await message.answer(f"❌ {error_message}. Попробуйте еще раз:")
        return

    # Подготавливаем данные для обновления
    update_data = prepare_product_data(field, new_value)

    # Обновляем товар в базе данных
    success = update_product(product_id, update_data)

    if success:
        product = get_product_details(product_id)

        await message.answer(
            "✅ <b>Товар успешно обновлен!</b>\n\n" +
            format_product_details(product),
            reply_markup=get_product_details_keyboard(product_id,
                                                      is_active=bool(product[9] if len(product) > 9 else 1)),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при обновлении товара!</b>\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=get_product_details_keyboard(product_id),
            parse_mode="HTML"
        )

    # Очищаем состояние
    await state.clear()


# Активация/деактивация товара
@router.callback_query(F.data.startswith("toggle_product:"))
async def cmd_toggle_product(callback: CallbackQuery):
    """Обработчик для активации/деактивации товара"""
    _, product_id, new_status = callback.data.split(":", 2)

    success = toggle_product_status(int(product_id), bool(int(new_status)))

    if success:
        product = get_product_details(int(product_id))

        await callback.message.edit_text(
            "✅ <b>Статус товара успешно изменен!</b>\n\n" +
            format_product_details(product),
            reply_markup=get_product_details_keyboard(product_id, is_active=bool(int(new_status))),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при изменении статуса товара!</b>\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=get_product_details_keyboard(product_id),
            parse_mode="HTML"
        )

    await callback.answer()


# Управление категориями
@router.callback_query(F.data == "manage_categories")
async def cmd_manage_categories(callback: CallbackQuery):
    """Обработчик для управления категориями"""
    await callback.message.edit_text(
        "🗂 <b>Управление категориями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_categories_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "add_category")
async def cmd_add_category(callback: CallbackQuery, state: FSMContext):
    """Обработчик для добавления новой категории"""
    await callback.message.edit_text(
        "➕ <b>Добавление новой категории</b>\n\n"
        "Введите название новой категории:",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.adding_category)
    await callback.answer()


@router.message(ProductStates.adding_category)
async def process_add_category(message: Message, state: FSMContext):
    """Обработчик ввода имени новой категории"""
    category_name = message.text.strip()

    if not category_name:
        await message.answer("❌ Название категории не может быть пустым. Попробуйте еще раз:")
        return

    success = add_category(category_name)

    if success:
        await message.answer(
            f"✅ <b>Категория '{category_name}' успешно добавлена!</b>",
            reply_markup=get_categories_management_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>Категория '{category_name}' уже существует или произошла ошибка!</b>",
            reply_markup=get_categories_management_keyboard(),
            parse_mode="HTML"
        )

    await state.clear()


@router.callback_query(F.data == "edit_categories")
async def cmd_edit_categories(callback: CallbackQuery):
    """Обработчик для выбора категории для редактирования"""
    categories = get_categories()

    await callback.message.edit_text(
        "✏️ <b>Выберите категорию для редактирования:</b>",
        reply_markup=get_category_selection_keyboard(categories, action="edit"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_category:"))
async def cmd_edit_category(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории для редактирования"""
    _, category = callback.data.split(":", 1)

    await state.update_data(old_category=category)

    await callback.message.edit_text(
        f"✏️ <b>Редактирование категории '{category}'</b>\n\n"
        "Введите новое название категории:",
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.editing_category)
    await callback.answer()


@router.message(ProductStates.editing_category)
async def process_edit_category(message: Message, state: FSMContext):
    """Обработчик ввода нового имени категории"""
    new_category = message.text.strip()

    if not new_category:
        await message.answer("❌ Название категории не может быть пустым. Попробуйте еще раз:")
        return

    # Получаем старое название категории
    data = await state.get_data()
    old_category = data.get('old_category')

    success = update_category(old_category, new_category)

    if success:
        await message.answer(
            f"✅ <b>Категория успешно переименована с '{old_category}' на '{new_category}'!</b>",
            reply_markup=get_categories_management_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при переименовании категории!</b>\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=get_categories_management_keyboard(),
            parse_mode="HTML"
        )

    await state.clear()


@router.callback_query(F.data == "delete_categories")
async def cmd_delete_categories(callback: CallbackQuery):
    """Обработчик для выбора категории для удаления"""
    categories = get_categories()

    await callback.message.edit_text(
        "❌ <b>Выберите категорию для удаления:</b>\n\n"
        "⚠️ <b>Внимание:</b> все товары в этой категории будут деактивированы!",
        reply_markup=get_category_selection_keyboard(categories, action="delete"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_category:"))
async def cmd_delete_category(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории для удаления"""
    _, category = callback.data.split(":", 1)

    await state.update_data(category_to_delete=category)

    await callback.message.edit_text(
        f"⚠️ <b>Вы уверены, что хотите удалить категорию '{category}'?</b>\n\n"
        "Все товары в этой категории будут деактивированы!",
        reply_markup=get_confirm_cancel_keyboard("delete_category"),
        parse_mode="HTML"
    )

    await state.set_state(ProductStates.confirming_category_delete)
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_category", ProductStates.confirming_category_delete)
async def cmd_confirm_delete_category(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения удаления категории"""
    # Получаем категорию для удаления
    data = await state.get_data()
    category = data.get('category_to_delete')

    success = delete_category(category)

    if success:
        await callback.message.edit_text(
            f"✅ <b>Категория '{category}' успешно удалена!</b>\n"
            "Все товары в этой категории деактивированы.",
            reply_markup=get_categories_management_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при удалении категории!</b>\n"
            "Пожалуйста, попробуйте еще раз.",
            reply_markup=get_categories_management_keyboard(),
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_category", ProductStates.confirming_category_delete)
async def cmd_cancel_delete_category(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены удаления категории"""
    await callback.message.edit_text(
        "🔄 <b>Удаление категории отменено!</b>",
        reply_markup=get_categories_management_keyboard(),
        parse_mode="HTML"
    )

    await state.clear()
    await callback.answer()


# Вспомогательные функции
async def show_products_list(message, user_id):
    """Показывает список товаров с пагинацией"""
    category = CURRENT_CATEGORY.get(user_id)
    page = CURRENT_PAGE.get(user_id, 1)

    products, total_pages = get_paginated_products(category, page)

    header = f"📦 <b>Товары{'</b>' if not category else f' категории {category}</b>'}"
    products_text = ""

    if not products:
        products_text = "\n\nТовары не найдены."

    await message.edit_text(
        f"{header}{products_text}",
        reply_markup=get_products_list_keyboard(products, category, page, total_pages),
        parse_mode="HTML"
    )
