import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

# Локальные импорты
from database.discounts_db import DiscountsDatabase
from database.warehouse_db import WarehouseDatabase
from states.discounts_admin_states import AdminActionStates
from keyboards.admins.discounts_admin_keyboards import (
    get_action_management_menu, get_all_actions_keyboard, ActionAdminCallback,
    get_action_admin_view_keyboard, get_action_delete_confirmation_keyboard,
    get_discount_type_keyboard, DiscountTypeCallback, get_calendar,
    get_action_fsm_nav_keyboard, get_action_confirmation_keyboard,
    get_action_target_type_keyboard, ActionTargetCallback,
    get_catalog_keyboard, ActionCatalogCallback, ActionPaginatorCallback,
    ActionEditCallback
)

actions_admin_router = Router()
db = DiscountsDatabase()
warehouse_db = WarehouseDatabase()

TOTAL_FSM_STEPS = 5


# --- Вспомогательные функции ---

def get_action_progress(step: int) -> str:
    """Возвращает строку с прогресс-баром."""
    filled = "██"
    empty = "░░"
    return f"<code>{filled * step}{empty * (TOTAL_FSM_STEPS - step)}</code>"


def get_action_breadcrumbs(step_name: str) -> str:
    """Возвращает строку 'хлебных крошек'."""
    return f"<i>Управление акциями / Создание / {step_name}</i>"


def format_action_details(action_data: list) -> str:
    """Форматирует детали акции для просмотра админом."""
    action = {
        'id': action_data[0], 'title': action_data[1], 'description': action_data[2],
        'product_id': action_data[3], 'discount_type': action_data[4], 'discount_value': action_data[5],
        'start_date': action_data[6], 'end_date': action_data[7], 'is_active': action_data[8],
        'created_at': action_data[9], 'created_by_id': action_data[10], 'created_by_username': action_data[11]
    }

    discount_str = f"{int(action['discount_value'])}%" if action[
                                                              'discount_type'] == 'percentage' else f"{int(action['discount_value'])} ₽"

    details = [
        f"🔥 <b>{action['title']}</b>",
        f"📄 <b>Описание:</b> {action['description']}",
        f"💸 <b>Скидка:</b> {discount_str}",
        f"<b>🗓️ Срок проведения:</b> с {action['start_date']} по {action['end_date']}",
    ]
    if action['product_id']:
        product_name = warehouse_db.get_product_name_by_id(action['product_id'])
        details.append(f"📦 <b>Товар:</b> {product_name} (ID: <code>{action['product_id']}</code>)")

    details.append("\n<b>-- Для администратора --</b>")
    details.append(f"<b>Статус:</b> {'Активна' if action['is_active'] else 'Неактивна'}")
    if action['created_by_username']:
        details.append(f"<b>Создал:</b> @{action['created_by_username']}")

    return "\n".join(details)


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ (просмотр, удаление, навигация) ---

@actions_admin_router.callback_query(F.data == "admin_manage_actions")
async def manage_actions_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите действие для акций:", reply_markup=get_action_management_menu())
    await callback.answer()


@actions_admin_router.callback_query(F.data == "action_list_all")
async def list_all_actions(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    all_actions = db.get_all_actions()
    await callback.message.edit_text(
        "Список всех акций:\n(✅-активная, ⏳-будущая, 🚫-прошедшая, ❌-неактивна)",
        reply_markup=get_all_actions_keyboard(all_actions)
    )
    await callback.answer()


@actions_admin_router.callback_query(ActionAdminCallback.filter("view" == F.action))
async def admin_view_action(callback: CallbackQuery, callback_data: ActionAdminCallback):
    action_raw = db.get_action_details(callback_data.action_id)
    if not action_raw:
        await callback.answer("Акция не найдена!", show_alert=True)
        return

    text = format_action_details(action_raw)
    await callback.message.edit_text(text, reply_markup=get_action_admin_view_keyboard(callback_data.action_id,
                                                                                       bool(action_raw[8])), parse_mode='HTML')
    await callback.answer()


@actions_admin_router.callback_query(ActionAdminCallback.filter("toggle" == F.action))
async def toggle_action_status(callback: CallbackQuery, callback_data: ActionAdminCallback):
    action_details = db.get_action_details(callback_data.action_id)
    new_status = not action_details[8]  # is_active
    db.update_action_status(callback_data.action_id, new_status)
    await callback.answer(f"Статус акции изменен на {'активна' if new_status else 'неактивна'}.")
    await admin_view_action(callback, callback_data)


@actions_admin_router.callback_query(ActionAdminCallback.filter("delete" == F.action))
async def delete_action_confirm(callback: CallbackQuery, callback_data: ActionAdminCallback):
    action_details = db.get_action_details(callback_data.action_id)
    title = action_details[1] if action_details else "???"
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить акцию '<b>{title}</b>'?\n\n<b>Это действие необратимо!</b>",
        reply_markup=get_action_delete_confirmation_keyboard(callback_data.action_id), parse_mode='HTML'
    )
    await callback.answer()


@actions_admin_router.callback_query(ActionAdminCallback.filter("confirm_delete" == F.action))
async def delete_action_final(callback: CallbackQuery, callback_data: ActionAdminCallback, state: FSMContext):
    db.delete_action(callback_data.action_id)
    await callback.answer("Акция удалена!", show_alert=True)
    await list_all_actions(callback, state)


# --- FSM ДЛЯ СОЗДАНИЯ НОВОЙ АКЦИИ ---

@actions_admin_router.callback_query(F.data == "action_create_start")
async def action_create_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminActionStates.enter_title)
    await callback.message.edit_text(
        f"{get_action_progress(1)}\n{get_action_breadcrumbs('Название')}\n\n"
        "<b>Шаг 1/5: Введите название акции.</b>\n\n"
        "Это будет заголовок, который увидят клиенты (например: 'Весенние скидки!').",
        reply_markup=get_action_fsm_nav_keyboard(), parse_mode='HTML'
    )


@actions_admin_router.message(AdminActionStates.enter_title)
async def process_action_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdminActionStates.enter_description)
    await message.answer(
        f"{get_action_progress(2)}\n{get_action_breadcrumbs('Описание')}\n\n"
        "<b>Шаг 2/5: Введите подробное описание акции.</b>",
        reply_markup=get_action_fsm_nav_keyboard(), parse_mode='HTML'
    )


@actions_admin_router.message(AdminActionStates.enter_description)
async def process_action_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AdminActionStates.choose_target_type)
    await message.answer(
        f"{get_action_progress(3)}\n{get_action_breadcrumbs('Выбор цели')}\n\n"
        "<b>Шаг 3/5: Выберите, на что будет действовать скидка.</b>",
        reply_markup=get_action_target_type_keyboard(), parse_mode='HTML'
    )


@actions_admin_router.callback_query(ActionTargetCallback.filter(), AdminActionStates.choose_target_type)
async def process_target_type(callback: CallbackQuery, callback_data: ActionTargetCallback, state: FSMContext):
    await state.update_data(target_type=callback_data.target_type)
    categories = warehouse_db.get_all_categories()
    if not categories:
        await callback.answer("В базе данных не найдено ни одной категории товаров!", show_alert=True)
        return
    await state.update_data(available_categories=categories)
    await state.set_state(AdminActionStates.choose_category)
    await callback.message.edit_text(
        f"{get_action_progress(3)}\n{get_action_breadcrumbs('Выбор Категории')}\n\n"
        "<b>Выберите категорию:</b>",
        reply_markup=get_catalog_keyboard(level='category', items=categories, page=0), parse_mode='HTML'
    )


@actions_admin_router.callback_query(ActionPaginatorCallback.filter())
async def process_pagination(callback: CallbackQuery, callback_data: ActionPaginatorCallback, state: FSMContext):
    data = await state.get_data()
    level, page = callback_data.level, callback_data.page
    items_map = {
        'category': data.get('available_categories', []),
        'product_name': data.get('available_product_names', []),
        'flavor': data.get('available_flavors', [])
    }
    await callback.message.edit_reply_markup(
        reply_markup=get_catalog_keyboard(level=level, items=items_map.get(level, []), page=page)
    )
    await callback.answer()


@actions_admin_router.callback_query(ActionCatalogCallback.filter(), StateFilter(AdminActionStates.choose_category,
                                                                                 AdminActionStates.choose_product_name,
                                                                                 AdminActionStates.choose_flavor))
async def process_catalog_choice(callback: CallbackQuery, callback_data: ActionCatalogCallback, state: FSMContext):
    data = await state.get_data()
    target_type, level, selected_index = data.get('target_type'), callback_data.level, int(callback_data.item_index)

    if level == 'category':
        category_name = data.get('available_categories', [])[selected_index]
        await state.update_data(category_name=category_name)
        if target_type == 'category':
            await state.update_data(product_id=None, target_name=f"Категория: {category_name}")
            await go_to_discount_step(callback, state)
        else:
            product_names = warehouse_db.get_product_names_by_category(category_name)
            await state.update_data(available_product_names=product_names)
            await state.set_state(AdminActionStates.choose_product_name)
            await callback.message.edit_text(
                f"{get_action_progress(3)}\n{get_action_breadcrumbs('Выбор Линейки')}\n\n"
                f"Категория: <b>{category_name}</b>\n<b>Выберите линейку товаров:</b>",
                reply_markup=get_catalog_keyboard(level='product_name', items=product_names, page=0), parse_mode='HTML'
            )
    elif level == 'product_name':
        product_name = data.get('available_product_names', [])[selected_index]
        await state.update_data(product_name=product_name)
        if target_type == 'product_name':
            await state.update_data(product_id=None, target_name=f"Линейка: {product_name}")
            await go_to_discount_step(callback, state)
        else:
            flavors = warehouse_db.get_flavors_by_product_name(product_name)
            await state.update_data(available_flavors=flavors)
            await state.set_state(AdminActionStates.choose_flavor)
            await callback.message.edit_text(
                f"{get_action_progress(3)}\n{get_action_breadcrumbs('Выбор Вкуса')}\n\n"
                f"Линейка: <b>{product_name}</b>\n<b>Выберите конкретный товар:</b>",
                reply_markup=get_catalog_keyboard(level='flavor', items=flavors, page=0), parse_mode='HTML'
            )
    elif level == 'flavor':
        product_id, product_full_name = data.get('available_flavors', [])[selected_index]
        await state.update_data(product_id=product_id, target_name=product_full_name)
        await go_to_discount_step(callback, state)


async def go_to_discount_step(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminActionStates.choose_discount_type)
    await callback.message.edit_text(
        f"{get_action_progress(4)}\n{get_action_breadcrumbs('Тип скидки')}\n\n"
        "<b>Шаг 4/5: Выберите тип скидки.</b>",
        reply_markup=get_discount_type_keyboard(), parse_mode='HTML'
    )


@actions_admin_router.callback_query(DiscountTypeCallback.filter(), AdminActionStates.choose_discount_type)
async def process_action_discount_type(callback: CallbackQuery, callback_data: DiscountTypeCallback, state: FSMContext):
    await state.update_data(discount_type=callback_data.type_name)
    await state.set_state(AdminActionStates.enter_discount_value)
    await callback.message.edit_text(
        f"{get_action_progress(4)}\n{get_action_breadcrumbs('Размер скидки')}\n\n"
        "<b>Шаг 4/5: Введите размер скидки (просто число).</b>",
        reply_markup=get_action_fsm_nav_keyboard(), parse_mode='HTML'
    )


@actions_admin_router.message(AdminActionStates.enter_discount_value)
async def process_action_discount_value(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        if value <= 0:
            await message.answer("Скидка должна быть больше нуля.")
            return
        await state.update_data(discount_value=value)
        await state.set_state(AdminActionStates.enter_start_date)
        await message.answer(
            f"{get_action_progress(5)}\n{get_action_breadcrumbs('Дата начала')}\n\n"
            "<b>Шаг 5/5: Выберите дату начала акции.</b>",
            reply_markup=await get_calendar(), parse_mode='HTML'
        )
    except ValueError:
        await message.answer("Ошибка. Введите число.")


@actions_admin_router.callback_query(SimpleCalendarCallback.filter(),
                                     StateFilter(AdminActionStates.enter_start_date, AdminActionStates.enter_end_date))
async def process_action_date_selection(callback: CallbackQuery, callback_data: SimpleCalendarCallback,
                                        state: FSMContext):
    calendar = SimpleCalendar(show_alerts=True)
    selected, date = await calendar.process_selection(callback, callback_data)
    current_state_str = await state.get_state()

    if selected:
        # --- Обработка выбора ДАТЫ НАЧАЛА ---
        if current_state_str == AdminActionStates.enter_start_date:
            selected_start_date = date.date()
            await state.update_data(start_date=selected_start_date.strftime('%Y-%m-%d'))
            await state.set_state(AdminActionStates.enter_end_date)

            # Показываем календарь для даты окончания, передавая дату начала как минимальную
            await callback.message.edit_text(
                f"{get_action_progress(5)}\n{get_action_breadcrumbs('Дата окончания')}\n\n"
                "<b>Шаг 5/5: Выберите дату окончания акции.</b>",
                reply_markup=await get_calendar(min_date=selected_start_date), parse_mode='HTML'
            )

        # --- Обработка выбора ДАТЫ ОКОНЧАНИЯ ---
        elif current_state_str == AdminActionStates.enter_end_date:
            data = await state.get_data()
            # Преобразуем строковую дату из state в объект date
            start_date_obj = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            selected_end_date = date.date()

            # --- ГЛАВНОЕ ИСПРАВЛЕНИЕ ---
            # Добавляем жесткую проверку на случай, если UI дал сбой
            if selected_end_date < start_date_obj:
                await callback.answer(
                    "❌ Дата окончания не может быть раньше даты начала!",
                    show_alert=True
                )
                # Перерисовываем клавиатуру, чтобы она не исчезла
                await callback.message.edit_reply_markup(
                    reply_markup=await get_calendar(min_date=start_date_obj)
                )
                return  # Прерываем выполнение, чтобы не идти дальше

            # Если все в порядке, сохраняем и идем к подтверждению
            await state.update_data(end_date=selected_end_date.strftime('%Y-%m-%d'))
            await show_action_confirmation_step(callback, state)


async def show_action_confirmation_step(callback_or_message: CallbackQuery | Message, state: FSMContext):
    data = await state.get_data()
    discount_str = f"{int(data.get('discount_value', 0))}%" if data.get(
        'discount_type') == 'percentage' else f"{int(data.get('discount_value', 0))} ₽"
    target_str = data.get('target_name', 'Не указана')
    text = (
        f"<b>Подтвердите создание акции:</b>\n\n"
        f"<b>Название:</b> {data.get('title')}\n"
        f"<b>Описание:</b> {data.get('description')}\n"
        f"<b>Цель акции:</b> {target_str}\n"
        f"<b>Скидка:</b> {discount_str}\n"
        f"<b>Начало:</b> {data.get('start_date')}\n"
        f"<b>Окончание:</b> {data.get('end_date')}\n"
    )
    await state.set_state(AdminActionStates.confirm_creation)
    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(text, reply_markup=get_action_confirmation_keyboard(),
                                                    parse_mode='HTML')
    else:
        await callback_or_message.answer(text, reply_markup=get_action_confirmation_keyboard(), parse_mode='HTML')


@actions_admin_router.callback_query(ActionEditCallback.filter(), AdminActionStates.confirm_creation)
async def edit_action_field(callback: CallbackQuery, callback_data: ActionEditCallback, state: FSMContext):
    await callback.answer(f"Логика редактирования для поля '{callback_data.field}' еще не реализована.",
                          show_alert=True)


@actions_admin_router.callback_query(F.data == "action_confirm_creation", AdminActionStates.confirm_creation)
async def save_action_to_db(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    data['created_by_id'] = callback.from_user.id
    data['created_by_username'] = callback.from_user.username
    try:
        db.add_action(data)
        await state.clear()
        await callback.message.edit_text(f"✅ Акция '<b>{data['title']}</b>' успешно создана!", parse_mode='HTML')
        await callback.message.answer("Вы в меню управления акциями.", reply_markup=get_action_management_menu(),
                                      )
    except Exception as e:
        await callback.message.edit_text(f"❌ Произошла ошибка при создании акции: {e}")
    finally:
        await callback.answer()
