import datetime
import secrets
import string

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram_calendar import SimpleCalendarCallback, SimpleCalendar

from database.discounts_db import DiscountsDatabase
from handlers.users.discounts_handler import format_promo_details
from states.discounts_admin_states import AdminPromoStates
from keyboards.admins.discounts_admin_keyboards import (
    get_admin_discounts_menu, get_promo_management_menu,
    get_all_promos_keyboard, get_discount_type_keyboard, get_skip_keyboard, get_cancel_keyboard,
    PromoAdminCallback, get_deal_management_menu, get_promo_admin_view_keyboard, get_promo_delete_confirmation_keyboard,
    DiscountTypeCallback, get_promo_confirmation_keyboard, PromoEditCallback, get_calendar,
    get_promo_code_input_keyboard, get_promo_generation_choice_keyboard
)

admin_discounts_router = Router()
db = DiscountsDatabase()

TOTAL_STEPS = 7


def generate_promo_code(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_progress_bar(current_step: int, total_steps: int) -> str:
    filled = "██"
    empty = "░░"
    progress = filled * current_step + empty * (total_steps - current_step)
    return f"<code>{progress}</code>"


async def show_confirmation_step(message_or_callback: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()

    discount_str = f"{int(data.get('discount_value', 0))}%" if data.get(
        'discount_type') == 'percentage' else f"{int(data.get('discount_value', 0))} ₽"
    text = (
        "<b>Проверьте и подтвердите данные:</b>\n\n"
        f"<b>Код:</b> <code>{data.get('code', '...')}</code>\n"
        f"<b>Описание:</b> {data.get('description', '...')}\n"
        f"<b>Скидка:</b> {discount_str}\n"
        f"<b>Мин. заказ:</b> {int(data.get('min_order_amount', 0))} ₽\n"
        f"<b>Действует до:</b> {data.get('end_date', '...')}\n"
        f"<b>Использований:</b> {data.get('max_uses', '...')}"
    )

    await state.set_state(AdminPromoStates.confirm_creation)

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=get_promo_confirmation_keyboard(),
                                                    parse_mode='HTML')
    else:
        await message_or_callback.answer(text, reply_markup=get_promo_confirmation_keyboard(), parse_mode='HTML')


@admin_discounts_router.callback_query(F.data == "fsm_cancel", StateFilter("*"))
async def cancel_fsm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.message.answer("Вы в меню управления скидками.", reply_markup=get_admin_discounts_menu(),
                                  parse_mode='HTML')
    await callback.answer()


@admin_discounts_router.callback_query(F.data == "admin_discounts_menu")
async def show_admin_discounts_menu(callback: CallbackQuery):
    await callback.message.edit_text("Панель управления акциями и скидками.", reply_markup=get_admin_discounts_menu(),
                                     parse_mode='HTML')
    await callback.answer()


@admin_discounts_router.callback_query(F.data == "admin_manage_promos")
async def manage_promos_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите действие для промокодов:", reply_markup=get_promo_management_menu(),
                                     parse_mode='HTML')
    await callback.answer()


@admin_discounts_router.callback_query(F.data == "promo_list_all")
async def list_all_promos(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    all_promos = db.get_all_promo_codes()
    await callback.message.edit_text(
        "Нажмите на промокод для детального просмотра и управления.\n(✅ - активен, ❌ - неактивен, 🚫 - просрочен)",
        reply_markup=get_all_promos_keyboard(all_promos), parse_mode='HTML'
    )
    await callback.answer()


@admin_discounts_router.callback_query(PromoAdminCallback.filter("view" == F.action))
async def admin_view_promo(callback: CallbackQuery, callback_data: PromoAdminCallback):
    promo_id = callback_data.promo_id
    promo_raw = db.get_promo_code_details(promo_id)
    if not promo_raw:
        await callback.answer("Промокод не найден!", show_alert=True)
        return

    promo_dict = {
        'id': promo_raw[0], 'code': promo_raw[1], 'description': promo_raw[2],
        'discount_type': promo_raw[3], 'discount_value': promo_raw[4],
        'min_order_amount': promo_raw[5], 'start_date': promo_raw[6],
        'end_date': promo_raw[7], 'is_active': promo_raw[8], 'max_uses': promo_raw[9],
        'current_uses': promo_raw[10]
    }
    created_by_username = promo_raw[13]

    user_view = format_promo_details(promo_dict)
    admin_view = (
        f"📊 <b>Статистика для администратора:</b>\n"
        f"<b>Статус:</b> {'Активен' if promo_dict['is_active'] else 'Неактивен'}\n"
        f"<b>Использовано:</b> {promo_dict['current_uses']} / {promo_dict['max_uses']}"
    )
    if created_by_username:
        admin_view += f"\n<b>Создал:</b> @{created_by_username}"

    full_text = f"{user_view}\n\n{admin_view}"
    await callback.message.edit_text(
        full_text,
        reply_markup=get_promo_admin_view_keyboard(promo_id, bool(promo_dict['is_active'])),
        parse_mode='HTML'
    )
    await callback.answer()


@admin_discounts_router.callback_query(PromoAdminCallback.filter("delete" == F.action))
async def delete_promo_confirm(callback: CallbackQuery, callback_data: PromoAdminCallback):
    promo_details = db.get_promo_code_details(callback_data.promo_id)
    code = promo_details[1] if promo_details else "???"
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить промокод <code>{code}</code>?\n\n<b>Это действие необратимо!</b>",
        reply_markup=get_promo_delete_confirmation_keyboard(callback_data.promo_id), parse_mode='HTML'
    )
    await callback.answer()


@admin_discounts_router.callback_query(PromoAdminCallback.filter("confirm_delete" == F.action))
async def delete_promo_final(callback: CallbackQuery, callback_data: PromoAdminCallback, state: FSMContext):
    db.delete_promo_code(callback_data.promo_id)
    await callback.answer("Промокод удален!", show_alert=True)
    await list_all_promos(callback, state)


@admin_discounts_router.callback_query(PromoAdminCallback.filter("toggle" == F.action))
async def toggle_promo_status(callback: CallbackQuery, callback_data: PromoAdminCallback):
    promo_details = db.get_promo_code_details(callback_data.promo_id)
    if not promo_details:
        await callback.answer("Промокод не найден!", show_alert=True)
        return

    new_status = not promo_details[8]
    db.update_promo_code_status(callback_data.promo_id, new_status)

    await callback.answer(f"Статус промокода изменен на {'активен' if new_status else 'неактивен'}.", parse_mode='HTML')

    all_promos = db.get_all_promo_codes()
    await callback.message.edit_text(
        "Список всех промокодов:",
        reply_markup=get_all_promos_keyboard(all_promos)
    )


@admin_discounts_router.callback_query(PromoAdminCallback.filter("delete" == F.action))
async def delete_promo(callback: CallbackQuery, callback_data: PromoAdminCallback):
    db.delete_promo_code(callback_data.promo_id)
    await callback.answer("Промокод успешно удален!", show_alert=True)

    all_promos = db.get_all_promo_codes()
    if not all_promos:
        await callback.message.edit_text("Все промокоды удалены.", reply_markup=get_promo_management_menu())
        return

    await callback.message.edit_text(
        "Список всех промокодов:",
        reply_markup=get_all_promos_keyboard(all_promos)
    )


# --- FSM для создания нового промокода ---

@admin_discounts_router.callback_query(F.data == "promo_create_start")
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminPromoStates.enter_code)
    progress = get_progress_bar(1, TOTAL_STEPS)
    await callback.message.edit_text(
        f"{progress}\n\n"
        "<b>Шаг 1/7: Введите промокод</b>\n\n"
        "Минимум 4 символа. Вы можете ввести свой или сгенерировать.",
        reply_markup=get_promo_code_input_keyboard(), parse_mode='HTML'
    )
    await callback.answer()


@admin_discounts_router.callback_query((F.data == "promo_generate_code") | (F.data == "promo_regenerate"),
                                       AdminPromoStates.enter_code)
async def generate_and_suggest_code(callback: CallbackQuery, state: FSMContext):
    new_code = generate_promo_code()
    while db.get_promo_code_by_code(new_code):
        new_code = generate_promo_code()

    await state.update_data(generated_code=new_code)

    progress = get_progress_bar(1, TOTAL_STEPS)
    await callback.message.edit_text(
        f"{progress}\n\n"
        f"Сгенерирован промокод: <code>{new_code}</code>\n\n"
        "<b>Что делаем дальше?</b>",
        reply_markup=get_promo_generation_choice_keyboard(), parse_mode='HTML'
    )
    await callback.answer()


@admin_discounts_router.callback_query(F.data == "promo_accept_generated", AdminPromoStates.enter_code)
async def accept_generated_code(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    generated_code = data.get('generated_code')

    if not generated_code:
        await callback.answer("Ошибка: сгенерированный код не найден. Попробуйте еще раз.", show_alert=True)
        return

    await state.update_data(code=generated_code)
    await state.set_state(AdminPromoStates.enter_description)
    progress = get_progress_bar(2, TOTAL_STEPS)
    await callback.message.edit_text(
        f"{progress}\n\n"
        f"Отлично! Используем код <code>{generated_code}</code>.\n\n"
        "<b>Шаг 2/7: Введите описание промокода для клиентов.</b>",
        reply_markup=get_cancel_keyboard(), parse_mode='HTML'
    )


@admin_discounts_router.callback_query(F.data == "promo_enter_manual", AdminPromoStates.enter_code)
async def switch_to_manual_input(callback: CallbackQuery):
    progress = get_progress_bar(1, TOTAL_STEPS)
    await callback.message.edit_text(
        f"{progress}\n\n"
        "<b>Шаг 1/7: Введите свой вариант промокода</b>\n\n"
        "Минимум 4 символа.",
        reply_markup=get_cancel_keyboard(), parse_mode='HTML'
    )


@admin_discounts_router.message(AdminPromoStates.enter_description)
async def process_promo_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()

    if data.get('editing_field'):
        await state.update_data(editing_field=None)
        await show_confirmation_step(message, state)
    else:
        await state.set_state(AdminPromoStates.choose_discount_type)
        progress = get_progress_bar(3, TOTAL_STEPS)
        await message.answer(f"{progress}\n\n<b>Шаг 3/7: Выберите тип скидки</b>",
                             reply_markup=get_discount_type_keyboard(), parse_mode='HTML')


@admin_discounts_router.message(AdminPromoStates.enter_code)
async def process_promo_code_fsm(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if len(code) < 4:
        await message.answer("❌ Длина промокода должна быть не менее 4 символов.", reply_markup=get_cancel_keyboard())
        return
    if db.get_promo_code_by_code(code):
        await message.answer("❌ Такой промокод уже существует.", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(code=code)
    data = await state.get_data()

    if data.get('editing_field'):
        await state.update_data(editing_field=None)
        await show_confirmation_step(message, state)
    else:
        await state.set_state(AdminPromoStates.enter_description)
        progress = get_progress_bar(2, TOTAL_STEPS)
        await message.answer(f"{progress}\n\n<b>Шаг 2/7: Введите описание.</b>", reply_markup=get_cancel_keyboard(),
                             parse_mode='HTML')


@admin_discounts_router.callback_query(DiscountTypeCallback.filter(), AdminPromoStates.choose_discount_type)
async def process_discount_type(callback: CallbackQuery, callback_data: DiscountTypeCallback, state: FSMContext):
    await state.update_data(discount_type=callback_data.type_name)
    await state.set_state(AdminPromoStates.enter_discount_value)
    prompt = "<b>Шаг 4/7: Введите значение скидки</b>\n\n- Для процентов: 10, 20\n- Для фикс. суммы: 100, 500"
    await callback.message.edit_text(prompt, reply_markup=get_cancel_keyboard(), parse_mode='HTML')
    await callback.answer()


@admin_discounts_router.message(AdminPromoStates.enter_discount_value)
async def process_discount_value(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        if value <= 0:
            await message.answer("❌ Значение скидки должно быть больше нуля.", reply_markup=get_cancel_keyboard())
            return

        await state.update_data(discount_value=value)
        data = await state.get_data()

        if data.get('editing_field'):
            await state.update_data(editing_field=None)
            await show_confirmation_step(message, state)
        else:
            await state.set_state(AdminPromoStates.enter_min_order_amount)
            progress = get_progress_bar(5, TOTAL_STEPS)
            await message.answer(f"{progress}\n\n<b>Шаг 5/7: Мин. сумма заказа</b> (0 - без ограничений)",
                                 reply_markup=get_cancel_keyboard(), parse_mode='HTML')
    except ValueError:
        await message.answer("Неверный формат. Пожалуйста, введите число.")


@admin_discounts_router.message(AdminPromoStates.enter_min_order_amount)
async def process_min_amount(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        if value < 0:
            await message.answer("❌ Минимальная сумма не может быть отрицательной.", reply_markup=get_cancel_keyboard())
            return

        await state.update_data(min_order_amount=value)
        data = await state.get_data()

        if data.get('editing_field'):
            await state.update_data(editing_field=None)
            await show_confirmation_step(message, state)
        else:
            await state.set_state(AdminPromoStates.enter_end_date)
            progress = get_progress_bar(6, TOTAL_STEPS)
            await message.answer(f"{progress}\n\n<b>Шаг 6/7: Выберите дату окончания</b>",
                                 reply_markup=await get_calendar(), parse_mode='HTML')
    except ValueError:
        await message.answer("Неверный формат. Пожалуйста, введите число.")


@admin_discounts_router.callback_query(SimpleCalendarCallback.filter(), AdminPromoStates.enter_end_date)
async def process_calendar_selection(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(datetime.datetime.now(), datetime.datetime(2026, 1, 1))

    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        await state.update_data(end_date=date.strftime('%Y-%m-%d'))
        data = await state.get_data()

        if data.get('editing_field'):
            await state.update_data(editing_field=None)
            await show_confirmation_step(callback, state)
        else:
            await state.set_state(AdminPromoStates.enter_max_uses)
            progress = get_progress_bar(7, TOTAL_STEPS)
            await callback.message.edit_text(
                f"{progress}\n\n<b>Шаг 7/7: Макс. кол-во использований (1-1000)</b>\n\nНажмите 'Пропустить' для безлимита.",
                reply_markup=get_skip_keyboard(), parse_mode='HTML')


@admin_discounts_router.callback_query(F.data == "skip_step", AdminPromoStates.enter_max_uses)
async def skip_max_uses(callback: CallbackQuery, state: FSMContext):
    await state.update_data(max_uses=999999)
    await show_confirmation_step(callback, state)
    await callback.answer()


@admin_discounts_router.message(AdminPromoStates.enter_max_uses)
async def process_max_uses(message: Message, state: FSMContext):
    try:
        value = int(message.text)
        if not (1 <= value <= 1000):
            await message.answer("❌ Введите число от 1 до 1000.", reply_markup=get_cancel_keyboard())
            return
        await state.update_data(max_uses=value)
        await show_confirmation_step(message, state)
    except ValueError:
        await message.answer("Неверный формат. Пожалуйста, введите целое число.")


async def confirm_promo_creation(message: Message, state: FSMContext):
    data = await state.get_data()
    today = datetime.date.today().isoformat()
    data.setdefault('start_date', today)

    discount_str = f"{int(data['discount_value'])}%" if data[
                                                            'discount_type'] == 'percentage' else f"{int(data['discount_value'])} ₽"
    text = (
        "<b>Проверьте данные перед созданием:</b>\n\n"
        f"<b>Код:</b> <code>{data['code']}</code>\n"
        f"<b>Описание:</b> {data['description']}\n"
        f"<b>Скидка:</b> {discount_str}\n"
        f"<b>Мин. заказ:</b> {int(data['min_order_amount'])} ₽\n"
        f"<b>Действует до:</b> {data['end_date']}\n"
        f"<b>Использований:</b> {data['max_uses']}"
    )
    await state.set_state(AdminPromoStates.confirm_creation)
    await message.answer(text, reply_markup=get_promo_confirmation_keyboard(), parse_mode='HTML')


@admin_discounts_router.callback_query(PromoEditCallback.filter(), AdminPromoStates.confirm_creation)
async def edit_promo_field(callback: CallbackQuery, callback_data: PromoEditCallback, state: FSMContext):
    field_to_edit = callback_data.field
    await state.update_data(editing_field=field_to_edit)

    field_map = {
        "code": (AdminPromoStates.enter_code, "Введите новый промокод:"),
        "description": (AdminPromoStates.enter_description, "Введите новое описание:"),
        "value": (AdminPromoStates.enter_discount_value, "Введите новое значение скидки:"),
        "min_amount": (AdminPromoStates.enter_min_order_amount, "Введите новую мин. сумму заказа:"),
        "end_date": (AdminPromoStates.enter_end_date, "Выберите новую дату:"),
        "max_uses": (AdminPromoStates.enter_max_uses, "Введите новое макс. кол-во использований:")
    }

    target_state, prompt_text = field_map[field_to_edit]
    await state.set_state(target_state)

    if field_to_edit == 'end_date':
        await callback.message.edit_text(prompt_text, reply_markup=await get_calendar())
    else:
        await callback.message.edit_text(prompt_text, reply_markup=get_cancel_keyboard())

    await callback.answer(f"Редактирование поля: {field_to_edit}")


@admin_discounts_router.callback_query(F.data == "confirm_action", AdminPromoStates.confirm_creation)
async def save_promo_to_db(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    data.setdefault('start_date', datetime.date.today().isoformat())
    data['created_by_id'] = callback.from_user.id
    data['created_by_username'] = callback.from_user.username

    required_keys = ['code', 'description', 'discount_type', 'discount_value', 'min_order_amount', 'start_date',
                     'end_date', 'max_uses']
    if not all(key in data for key in required_keys):
        await callback.answer("Произошла ошибка, не все данные были заполнены. Попробуйте снова.", show_alert=True)
        await state.clear()
        await callback.message.edit_text("Ошибка. Создание отменено.", reply_markup=get_promo_management_menu())
        return

    db.add_promo_code(data)

    await state.clear()
    await callback.message.edit_text(f"✅ Промокод <code>{data['code']}</code> успешно создан!", parse_mode='HTML')
    await callback.message.answer("Вы в меню управления промокодами.", reply_markup=get_promo_management_menu())
    await callback.answer()


@admin_discounts_router.callback_query(F.data == "cancel_action", AdminPromoStates.confirm_creation)
async def cancel_promo_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание промокода отменено.", reply_markup=get_promo_management_menu())
    await callback.answer()


@admin_discounts_router.callback_query(F.data == "admin_manage_deals")
async def manage_deals_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите действие для 'Товара дня':",
        reply_markup=get_deal_management_menu()
    )
    await callback.answer()
