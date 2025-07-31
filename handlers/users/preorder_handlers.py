from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from datetime import datetime
import logging

from database.preorder_db import preorder_db
from keyboards.users.preorder_keyboards import (
    get_preorder_categories_keyboard,
    get_preorder_products_keyboard,
    get_preorder_flavors_keyboard,
    get_product_card_keyboard,
    get_my_preorders_keyboard, get_cancellation_reason_keyboard, get_back_to_card_keyboard
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "profile:preorders")
async def show_preorder_categories(callback: CallbackQuery):
    """Показать категории товаров для предзаказа"""
    categories = preorder_db.get_categories_with_ids()

    if not categories:
        await callback.message.edit_text(
            "🚫 Пока нет товаров для предзаказа.\n"
            "Загляните позже!",
            reply_markup=get_my_preorders_keyboard(1, 1)
        )
    else:
        await callback.message.edit_text(
            "📦 <b>Товары, которые скоро поступят в продажу</b>\n\n"
            "Выберите категорию:",
            reply_markup=get_preorder_categories_keyboard(categories),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "po:main")
async def back_to_categories(callback: CallbackQuery):
    """Вернуться к категориям"""
    await show_preorder_categories(callback)


@router.callback_query(F.data.startswith("po:c:"))
async def show_category_products(callback: CallbackQuery):
    """Показать товары в категории"""
    category_id = int(callback.data.split(":")[2])
    category_name = preorder_db.get_category_by_id(category_id)

    if not category_name:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    products = preorder_db.get_products_ids_by_category(category_id)

    if not products:
        await callback.answer("В этой категории пока нет товаров", show_alert=True)
        return

    breadcrumbs = f"📍 {category_name}"

    # Проверяем, является ли текущее сообщение фото
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            f"{breadcrumbs}\n\n"
            f"🛍️ <b>Товары в категории {category_name}</b>\n\n"
            "Выберите товар:",
            reply_markup=get_preorder_products_keyboard(category_id, products),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"{breadcrumbs}\n\n"
            f"🛍️ <b>Товары в категории {category_name}</b>\n\n"
            "Выберите товар:",
            reply_markup=get_preorder_products_keyboard(category_id, products),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("po:p:"))
async def show_product_flavors(callback: CallbackQuery):
    """Показать вкусы товара"""
    parts = callback.data.split(":")
    category_id = int(parts[2])
    product_id = int(parts[3])

    # Получаем информацию о товаре
    product_info = preorder_db.get_product_by_id(product_id)
    if not product_info:
        await callback.answer("Товар не найден", show_alert=True)
        return

    category_name = preorder_db.get_category_by_id(category_id)
    flavors = preorder_db.get_flavors_ids_by_product(category_id, product_id)

    if not flavors:
        await callback.answer("У этого товара пока нет доступных вкусов", show_alert=True)
        return

    breadcrumbs = f"📍 {category_name} → {product_info['product_name']}"

    # Проверяем, является ли текущее сообщение фото
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            f"{breadcrumbs}\n\n"
            f"🍓 <b>Доступные вкусы {product_info['product_name']}</b>\n\n"
            "Выберите вкус:",
            reply_markup=get_preorder_flavors_keyboard(category_id, product_id, flavors),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"{breadcrumbs}\n\n"
            f"🍓 <b>Доступные вкусы {product_info['product_name']}</b>\n\n"
            "Выберите вкус:",
            reply_markup=get_preorder_flavors_keyboard(category_id, product_id, flavors),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("po:f:"))
async def show_product_card(callback: CallbackQuery):
    """Показать карточку товара"""
    product_id = int(callback.data.split(":")[2])

    product = preorder_db.get_product_by_id(product_id)

    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Увеличиваем счетчик просмотров (только уникальные)
    user_id = callback.from_user.id
    preorder_db.increment_views(product['id'], user_id)

    # Получаем количество ожидающих
    preorders_count = preorder_db.get_product_preorders_count(product['id'])

    # Проверяем, есть ли у пользователя предзаказ
    has_preorder = preorder_db.has_preorder(user_id, product['id'])

    # Форматируем дату
    expected_date = "Не указана"
    if product['expected_date']:
        expected_date = datetime.strptime(product['expected_date'], '%Y-%m-%d').strftime('%d.%m.%Y')

    # Получаем ID категории для навигации
    category_id = preorder_db.get_category_id(product['category'])

    # Получаем ID родительского товара для навигации назад
    parent_products = preorder_db.get_products_ids_by_category(category_id)
    parent_product_id = next((p['id'] for p in parent_products if p['name'] == product['product_name']), product_id)

    # Формируем хлебные крошки
    breadcrumbs = f"📍 {product['category']} → {product['product_name']} → {product['flavor']}"

    # Формируем текст карточки
    text = (
        f"{breadcrumbs}\n"
        f"{'━' * 30}\n\n"
        f"<b>{product['product_name']}</b>\n"
        f"🍓 Вкус: {product['flavor']}\n\n"
    )

    if product['description']:
        text += f"📝 {product['description']}\n\n"

    if product['price']:
        text += f"💰 Цена: {product['price']} ₽\n"
    else:
        text += "💰 Цена: Уточняется\n"

    text += (
        f"📅 Ожидаемая дата поставки: {expected_date}\n"
        f"👁 Просмотров: {product['views']}\n"
        f"👥 Ожидают: {preorders_count} чел.\n"  # Добавьте эту строку
    )

    if has_preorder:
        text += "\n✅ <b>Вы уже сделали предзаказ на этот товар</b>"

    # Отправляем карточку товара
    if callback.message.photo:
        await callback.message.delete()

        if product['image_path']:
            try:
                photo = FSInputFile(product['image_path'])
                await callback.message.answer_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=get_product_card_keyboard(
                        product['id'], has_preorder, category_id, parent_product_id
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке изображения: {e}")
                await callback.message.answer(
                    text,
                    reply_markup=get_product_card_keyboard(
                        product['id'], has_preorder, category_id, parent_product_id
                    ),
                    parse_mode="HTML"
                )
        else:
            await callback.message.answer(
                text,
                reply_markup=get_product_card_keyboard(
                    product['id'], has_preorder, category_id, parent_product_id
                ),
                parse_mode="HTML"
            )
    else:
        if product['image_path']:
            try:
                photo = FSInputFile(product['image_path'])
                await callback.message.delete()
                await callback.message.answer_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=get_product_card_keyboard(
                        product['id'], has_preorder, category_id, parent_product_id
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке изображения: {e}")
                await callback.message.edit_text(
                    text,
                    reply_markup=get_product_card_keyboard(
                        product['id'], has_preorder, category_id, parent_product_id
                    ),
                    parse_mode="HTML"
                )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=get_product_card_keyboard(
                    product['id'], has_preorder, category_id, parent_product_id
                ),
                parse_mode="HTML"
            )

    await callback.answer()


@router.callback_query(F.data.startswith("po:make:"))
async def make_preorder(callback: CallbackQuery):
    """Сделать предзаказ"""
    product_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    if preorder_db.add_preorder(user_id, product_id):
        await callback.answer("✅ Предзаказ успешно оформлен!", show_alert=True)

        # Получаем информацию о товаре для обновления клавиатуры
        product = preorder_db.get_product_by_id(product_id)
        if product:
            category_id = preorder_db.get_category_id(product['category'])
            parent_products = preorder_db.get_products_ids_by_category(category_id)
            parent_product_id = next((p['id'] for p in parent_products if p['name'] == product['product_name']),
                                     product_id)

            new_keyboard = get_product_card_keyboard(
                product_id, True, category_id, parent_product_id
            )
            await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    else:
        await callback.answer("❌ Ошибка при оформлении предзаказа", show_alert=True)


@router.callback_query(F.data.startswith("po:cancel:"))
async def request_cancellation_reason(callback: CallbackQuery, state: FSMContext):
    """Запросить причину отмены предзаказа"""
    product_id = int(callback.data.split(":")[2])

    # Сохраняем ID товара в состоянии
    await state.update_data(cancelling_product_id=product_id)

    await callback.message.edit_text(
        "❓ <b>Почему вы решили отменить предзаказ?</b>\n\n"
        "Это поможет нам стать лучше:",
        reply_markup=get_cancellation_reason_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("po:reason:"))
async def process_cancellation_reason(callback: CallbackQuery, state: FSMContext):
    """Обработать причину отказа"""
    reason_code = callback.data.split(":")[2]
    data = await state.get_data()
    product_id = data.get('cancelling_product_id')

    if not product_id:
        await callback.answer("Ошибка: товар не найден", show_alert=True)
        return

    user_id = callback.from_user.id

    if reason_code == "other":
        # Запрашиваем пользовательскую причину
        await state.set_state("waiting_custom_reason")
        await callback.message.edit_text(
            "📝 Пожалуйста, напишите свою причину отказа:",
            reply_markup=get_back_to_card_keyboard(product_id)
        )
    else:
        # Сохраняем причину и отменяем предзаказ
        preorder_db.save_cancellation_reason(user_id, product_id, reason_code)

        if preorder_db.cancel_preorder(user_id, product_id):
            await callback.message.edit_text(
                "✅ Предзаказ отменен.\n\n"
                "Спасибо за обратную связь! Это поможет нам стать лучше.",
                reply_markup=get_back_to_card_keyboard(product_id)
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка при отмене предзаказа",
                reply_markup=get_back_to_card_keyboard(product_id)
            )

        await state.clear()

    await callback.answer()


@router.message(StateFilter("waiting_custom_reason"))
async def process_custom_reason(message: Message, state: FSMContext):
    """Обработать пользовательскую причину отказа"""
    data = await state.get_data()
    product_id = data.get('cancelling_product_id')

    if not product_id:
        await message.answer("Ошибка: товар не найден")
        return

    user_id = message.from_user.id
    custom_reason = message.text

    # Сохраняем причину и отменяем предзаказ
    preorder_db.save_cancellation_reason(user_id, product_id, "other", custom_reason)

    if preorder_db.cancel_preorder(user_id, product_id):
        await message.answer(
            "✅ Предзаказ отменен.\n\n"
            "Спасибо за обратную связь! Это поможет нам стать лучше.",
            reply_markup=get_back_to_card_keyboard(product_id)
        )
    else:
        await message.answer(
            "❌ Ошибка при отмене предзаказа",
            reply_markup=get_back_to_card_keyboard(product_id)
        )

    await state.clear()


@router.callback_query(F.data == "po:cancel_reason")
async def cancel_reason_dialog(callback: CallbackQuery, state: FSMContext):
    """Отменить диалог выбора причины"""
    data = await state.get_data()
    product_id = data.get('cancelling_product_id')

    if product_id:
        # Возвращаемся к карточке товара
        await state.clear()
        callback.data = f"po:f:{product_id}"
        await show_product_card(callback)
    else:
        await callback.answer("Ошибка: товар не найден", show_alert=True)


@router.callback_query(F.data == "profile:my_preorders")
async def show_my_preorders(callback: CallbackQuery):
    """Показать предзаказы пользователя"""
    await display_user_preorders(callback, page=1)


@router.callback_query(F.data.startswith("po:my:page:"))
async def show_preorders_page(callback: CallbackQuery):
    """Показать конкретную страницу предзаказов"""
    page = int(callback.data.split(":")[3])
    await display_user_preorders(callback, page=page)


async def display_user_preorders(callback: CallbackQuery, page: int):
    """Отобразить предзаказы пользователя с пагинацией"""
    user_id = callback.from_user.id
    data = preorder_db.get_user_preorders(user_id, page=page)

    if not data['items']:
        text = "У вас пока нет активных предзаказов."
    else:
        text = "📋 <b>Ваши предзаказы:</b>\n\n"
        start_idx = (page - 1) * 6 + 1

        for i, order in enumerate(data['items'], start_idx):
            expected_date = "Не указана"
            if order['expected_date']:
                expected_date = datetime.strptime(
                    order['expected_date'], '%Y-%m-%d'
                ).strftime('%d.%m.%Y')

            price_text = f"{order['price']} ₽" if order['price'] else "Уточняется"

            text += (
                f"{i}. {order['product_name']} ({order['flavor']})\n"
                f"   💰 {price_text}\n"
                f"   📅 Ожидается: {expected_date}\n\n"
            )

        if data['total_pages'] > 1:
            text += f"\nСтраница {page} из {data['total_pages']}"

    await callback.message.edit_text(
        text,
        reply_markup=get_my_preorders_keyboard(page, data['total_pages']),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "po:my:current")
async def handle_current_page(callback: CallbackQuery):
    """Обработка нажатия на текущую страницу"""
    await callback.answer()