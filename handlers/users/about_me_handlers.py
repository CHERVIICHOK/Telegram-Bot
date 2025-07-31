import logging
import re
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.users.about_me_db import (
    get_user_personal_info, update_user_personal_info,
    get_user_addresses, add_user_address, update_user_address,
    delete_user_address, set_default_address,
    get_delivery_preferences, update_delivery_preferences,
    log_user_action, update_courier_instructions
)
from keyboards.users.about_me_keyboards import (
    get_about_me_menu_keyboard, get_personal_info_keyboard,
    get_gender_keyboard, get_addresses_keyboard,
    get_address_detail_keyboard,
    get_delivery_time_keyboard, get_time_selection_keyboard,
    get_cancel_keyboard, get_skip_keyboard
)
from keyboards.users.profile_keyboards import get_profile_keyboard
from states.about_me_state import AboutMeStates

logger = logging.getLogger(__name__)
router = Router()


# ==================== Главное меню "О себе" ====================

@router.callback_query(F.data == "profile:about_me")
async def show_about_me_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает главное меню раздела 'О себе'"""
    await callback.answer()

    # Логируем просмотр главного меню
    log_user_action(callback.from_user.id, "viewed_about_me_menu")

    await callback.message.edit_text(
        "📝 <b>О себе</b>\n\n"
        "Здесь вы можете указать информацию о себе для более персонализированного обслуживания.",
        reply_markup=get_about_me_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.MAIN_MENU)


@router.callback_query(F.data == "about_me:data_security")
async def show_data_security_info(callback: CallbackQuery):
    """Показывает информацию о безопасности данных"""
    await callback.answer()

    # Логируем просмотр информации о безопасности
    log_user_action(callback.from_user.id, "viewed_data_security")

    security_text = (
        "🔒 <b>О безопасности ваших данных</b>\n\n"
        "🛡 <b>Зачем нам нужна эта информация?</b>\n"
        "• Для персонализации предложений и рекомендаций\n"
        "• Для удобства оформления заказов\n"
        "• Для своевременной доставки в удобное для вас время\n"
        "• Для улучшения качества обслуживания\n\n"
        "🔐 <b>Как мы защищаем ваши данные?</b>\n"
        "• Все данные надежно зашифрованы\n"
        "• Мы не передаем информацию третьим лицам\n"
        "• Вы можете удалить свои данные в любой момент\n\n"
        "✅ Мы соблюдаем все требования законодательства о защите персональных данных"
    )

    await callback.message.edit_text(
        security_text,
        reply_markup=get_about_me_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "about_me:back_to_profile", StateFilter(AboutMeStates))
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Возврат в профиль"""
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        "👤 <b>Личный кабинет</b>\n\n"
        "Выберите интересующий раздел:",
        reply_markup=get_profile_keyboard(),
        parse_mode="HTML"
    )


# ==================== Личные данные ====================

@router.callback_query(F.data == "about_me:personal_info")
async def show_personal_info(callback: CallbackQuery, state: FSMContext):
    """Показывает меню личных данных"""
    await callback.answer(
        "Мы будем учитывать введенные данные для персонализации сервиса и улучшения качества обслуживания",
        show_alert=True
    )

    # Логируем просмотр личных данных
    log_user_action(callback.from_user.id, "viewed_personal_info")

    user_info = get_user_personal_info(callback.from_user.id)

    text = "👤 <b>Личные данные</b>\n\n"
    text += "Нажмите на поле для редактирования:"

    await callback.message.edit_text(
        text,
        reply_markup=get_personal_info_keyboard(user_info),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.PERSONAL_INFO_MENU)


@router.callback_query(F.data == "personal:back", StateFilter(AboutMeStates.PERSONAL_INFO_MENU))
async def back_from_personal_info(callback: CallbackQuery, state: FSMContext):
    """Возврат из личных данных в главное меню"""
    await show_about_me_menu(callback, state)


# Редактирование имени
@router.callback_query(F.data == "personal:edit_first_name")
async def edit_first_name(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование имени"""
    await callback.answer()

    # Логируем начало редактирования
    log_user_action(callback.from_user.id, "started_editing_first_name")

    await callback.message.edit_text(
        "✏️ <b>Введите ваше имя:</b>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_FIRST_NAME)


@router.message(StateFilter(AboutMeStates.EDITING_FIRST_NAME))
async def process_first_name(message: Message, state: FSMContext):
    """Обрабатывает введенное имя"""
    first_name = message.text.strip()

    if len(first_name) < 2:
        await message.answer(
            "❌ Имя должно содержать минимум 2 символа. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if update_user_personal_info(message.from_user.id, 'first_name', first_name):
        await message.answer("✅", reply_markup=None)
        await show_personal_info_message(message, state)
    else:
        await message.answer("❌ Ошибка при обновлении имени. Попробуйте позже.")


# Редактирование фамилии
@router.callback_query(F.data == "personal:edit_last_name")
async def edit_last_name(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование фамилии"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_editing_last_name")

    await callback.message.edit_text(
        "✏️ <b>Введите вашу фамилию:</b>",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_LAST_NAME)


@router.message(StateFilter(AboutMeStates.EDITING_LAST_NAME))
async def process_last_name(message: Message, state: FSMContext):
    """Обрабатывает введенную фамилию"""
    last_name = message.text.strip()

    if len(last_name) < 2:
        await message.answer(
            "❌ Фамилия должна содержать минимум 2 символа. Попробуйте еще раз:",
            reply_markup=get_skip_keyboard()
        )
        return

    if update_user_personal_info(message.from_user.id, 'last_name', last_name):
        await message.answer("✅", reply_markup=None)
        await show_personal_info_message(message, state)
    else:
        await message.answer("❌ Ошибка при обновлении фамилии. Попробуйте позже.")


# Редактирование даты рождения
@router.callback_query(F.data == "personal:edit_birth_date")
async def edit_birth_date(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование даты рождения"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_editing_birth_date")

    await callback.message.edit_text(
        "📅 <b>Введите дату рождения в формате ДД.ММ:</b>\n"
        "Например: 01.09",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_BIRTH_DATE)


@router.message(StateFilter(AboutMeStates.EDITING_BIRTH_DATE))
async def process_birth_date(message: Message, state: FSMContext):
    """Обрабатывает введенную дату рождения"""
    birth_date = message.text.strip()

    # Валидация формата даты
    date_pattern = r'^\d{2}\.\d{2}$'
    if not re.match(date_pattern, birth_date):
        await message.answer(
            "❌ Неверный формат даты. Используйте формат ДД.ММ\n"
            "Например: 01.09",
            reply_markup=get_skip_keyboard()
        )
        return

    try:
        date_obj = datetime.strptime(birth_date, "%d.%m")

        if date_obj > datetime.now():
            await message.answer(
                "❌ Дата рождения не может быть в будущем!",
                reply_markup=get_skip_keyboard()
            )
            return

        # # Проверка на слишком старую дату
        # if date_obj.year < 1930:
        #     await message.answer(
        #         "❌ Пожалуйста, введите корректную дату рождения.",
        #         reply_markup=get_skip_keyboard()
        #     )
        #     return

    except ValueError:
        await message.answer(
            "❌ Некорректная дата. Проверьте правильность ввода.",
            reply_markup=get_skip_keyboard()
        )
        return

    if update_user_personal_info(message.from_user.id, 'birth_date', birth_date):
        await message.answer("✅ Данные успешно обновлены")
        await show_personal_info_message(message, state)
    else:
        await message.answer("❌ Ошибка при обновлении даты рождения. Попробуйте позже.")


# Выбор пола
@router.callback_query(F.data == "personal:edit_gender")
async def edit_gender(callback: CallbackQuery, state: FSMContext):
    """Показывает меню выбора пола"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_editing_gender")

    await callback.message.edit_text(
        "👤 <b>Выберите пол:</b>",
        reply_markup=get_gender_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.SELECTING_GENDER)


@router.callback_query(F.data.startswith("gender:"), StateFilter(AboutMeStates.SELECTING_GENDER))
async def process_gender_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор пола"""
    action = callback.data.split(':')[1]

    if action == "cancel":
        await callback.answer()
        log_user_action(callback.from_user.id, "cancelled_editing_gender")
        await show_personal_info(callback, state)
        return

    gender_map = {
        'male': 'Мужской',
        'female': 'Женский',
        'skip': 'Не указан'
    }

    gender = gender_map.get(action)

    if update_user_personal_info(callback.from_user.id, 'gender', gender):
        await callback.answer("Пол успешно обновлен!", show_alert=True)
        await show_personal_info(callback, state)
    else:
        await callback.answer("❌ Ошибка при обновлении пола", show_alert=True)


# Редактирование email
@router.callback_query(F.data == "personal:edit_email")
async def edit_email(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование email"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_editing_email")

    await callback.message.edit_text(
        "📧 <b>Введите ваш email:</b>",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_EMAIL)


@router.message(StateFilter(AboutMeStates.EDITING_EMAIL))
async def process_email(message: Message, state: FSMContext):
    """Обрабатывает введенный email"""
    email = message.text.strip()

    # Валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        await message.answer(
            "❌ Неверный формат email. Пожалуйста, введите корректный адрес.",
            reply_markup=get_skip_keyboard()
        )
        return

    if update_user_personal_info(message.from_user.id, 'email', email):
        await message.answer("✅", reply_markup=None)
        await show_personal_info_message(message, state)
    else:
        await message.answer("❌ Ошибка при обновлении email. Попробуйте позже.")


# Редактирование телефона
@router.callback_query(F.data == "personal:edit_phone")
async def edit_phone(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование телефона"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_editing_phone")

    await callback.message.edit_text(
        "📱 <b>Введите номер телефона:</b>\n"
        "Формат: +7XXXXXXXXXX или 8XXXXXXXXXX",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_PHONE)


@router.message(StateFilter(AboutMeStates.EDITING_PHONE))
async def process_phone(message: Message, state: FSMContext):
    """Обрабатывает введенный телефон"""
    phone = message.text.strip()

    # Убираем все лишние символы
    phone_digits = re.sub(r'\D', '', phone)

    # Проверка формата российского номера
    if phone_digits.startswith('7') and len(phone_digits) == 11:
        formatted_phone = f"+{phone_digits}"
    elif phone_digits.startswith('8') and len(phone_digits) == 11:
        formatted_phone = f"+7{phone_digits[1:]}"
    else:
        await message.answer(
            "❌ Неверный формат номера. Используйте формат +7XXXXXXXXXX или 8XXXXXXXXXX",
            reply_markup=get_skip_keyboard()
        )
        return

    if update_user_personal_info(message.from_user.id, 'phone', formatted_phone):
        await message.answer("✅", reply_markup=None)
        await show_personal_info_message(message, state)
    else:
        await message.answer("❌ Ошибка при обновлении номера. Попробуйте позже.")


# ==================== Адреса доставки ====================

@router.callback_query(F.data == "about_me:addresses")
async def show_addresses(callback: CallbackQuery, state: FSMContext):
    """Показывает список адресов"""
    await callback.answer(
        "Сохраненные адреса помогут быстрее оформлять заказы и планировать доставку",
        show_alert=True
    )

    log_user_action(callback.from_user.id, "viewed_addresses")

    addresses = get_user_addresses(callback.from_user.id)

    text = "📍 <b>Адреса доставки</b>\n\n"
    if addresses:
        text += "Ваши сохраненные адреса:\n\n"
        for i, addr in enumerate(addresses, 1):
            default_mark = " ⭐" if addr['is_default'] else ""
            text += f"{i}. {addr['address']}{default_mark}\n"
    else:
        text += "У вас пока нет сохраненных адресов."

    await callback.message.edit_text(
        text,
        reply_markup=get_addresses_keyboard(addresses),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.ADDRESS_MENU)


@router.callback_query(F.data == "address:back", StateFilter(AboutMeStates))
async def back_from_addresses(callback: CallbackQuery, state: FSMContext):
    """Возврат из адресов в главное меню"""
    await show_about_me_menu(callback, state)


@router.callback_query(F.data == "address:list", StateFilter(AboutMeStates))
async def show_address_list(callback: CallbackQuery, state: FSMContext):
    """Показывает список адресов"""
    await show_addresses(callback, state)


@router.callback_query(F.data.startswith("address:view_"))
async def view_address_detail(callback: CallbackQuery, state: FSMContext):
    """Показывает детали адреса"""
    await callback.answer()

    address_id = int(callback.data.split('_')[1])
    addresses = get_user_addresses(callback.from_user.id)

    address = next((addr for addr in addresses if addr['id'] == address_id), None)

    if not address:
        await callback.answer("❌ Адрес не найден", show_alert=True)
        await show_addresses(callback, state)
        return

    text = f"📍 <b>Адрес доставки</b>\n\n"
    text += f"{address['address']}\n"

    if address.get('courier_instructions'):
        text += f"\n📝 <b>Инструкции для курьера:</b>\n{address['courier_instructions']}\n"

    if address['is_default']:
        text += "\n⭐ <i>Основной адрес</i>"

    await callback.message.edit_text(
        text,
        reply_markup=get_address_detail_keyboard(address_id, address['is_default']),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "address:add_new")
async def add_new_address(callback: CallbackQuery, state: FSMContext):
    """Начинает добавление нового адреса"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_adding_address")

    await callback.message.edit_text(
        "📍 <b>Добавление нового адреса</b>\n\n"
        "Введите полный адрес доставки:\n"
        "Например: г. Москва, ул. Пушкина, д. 10, кв. 5",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.ADDING_ADDRESS)


@router.message(StateFilter(AboutMeStates.ADDING_ADDRESS))
async def process_new_address(message: Message, state: FSMContext):
    """Обрабатывает введенный адрес"""
    address = message.text.strip()

    if len(address) < 10:
        await message.answer(
            "❌ Пожалуйста, введите полный адрес доставки:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Если это первый адрес, делаем его основным
    addresses = get_user_addresses(message.from_user.id)
    is_default = len(addresses) == 0

    if add_user_address(message.from_user.id, address, is_default):
        await message.answer("✅", reply_markup=None)
        await show_addresses_message(message, state)
    else:
        await message.answer("❌ Ошибка при добавлении адреса. Попробуйте позже.")


@router.callback_query(F.data.startswith("address:edit_"))
async def edit_address(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование адреса"""
    await callback.answer()

    address_id = int(callback.data.split('_')[1])
    await state.update_data(editing_address_id=address_id)

    log_user_action(callback.from_user.id, "started_editing_address", f"id:{address_id}")

    await callback.message.edit_text(
        "✏️ <b>Введите новый адрес:</b>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_ADDRESS)


@router.message(StateFilter(AboutMeStates.EDITING_ADDRESS))
async def process_edited_address(message: Message, state: FSMContext):
    """Обрабатывает отредактированный адрес"""
    address = message.text.strip()

    if len(address) < 10:
        await message.answer(
            "❌ Пожалуйста, введите полный адрес доставки:",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    address_id = data['editing_address_id']

    if update_user_address(address_id, message.from_user.id, address):
        await message.answer("✅", reply_markup=None)
        await show_addresses_message(message, state)
    else:
        await message.answer("❌ Ошибка при обновлении адреса. Попробуйте позже.")


@router.callback_query(F.data.startswith("address:set_default_"))
async def set_address_default(callback: CallbackQuery, state: FSMContext):
    """Устанавливает адрес по умолчанию"""
    address_id = int(callback.data.split('_')[2])

    if set_default_address(address_id, callback.from_user.id):
        await callback.answer("✅ Адрес установлен как основной!", show_alert=True)
        # Исправление бага - используем существующий callback
        callback.data = f"address:view_{address_id}"
        await view_address_detail(callback, state)
    else:
        await callback.answer("❌ Ошибка при установке адреса", show_alert=True)


@router.callback_query(F.data.startswith("address:delete_"))
async def delete_address(callback: CallbackQuery, state: FSMContext):
    """Удаляет адрес"""
    address_id = int(callback.data.split('_')[1])

    if delete_user_address(address_id, callback.from_user.id):
        await callback.answer("✅ Адрес удален!", show_alert=True)
        await show_addresses(callback, state)
    else:
        await callback.answer("❌ Ошибка при удалении адреса", show_alert=True)


# ==================== Время доставки ====================

@router.callback_query(F.data == "about_me:delivery_time")
async def show_delivery_time(callback: CallbackQuery, state: FSMContext):
    """Показывает настройки времени доставки"""
    await callback.answer(
        "Укажите удобное время, и мы постараемся доставлять заказы в этот интервал",
        show_alert=True
    )

    log_user_action(callback.from_user.id, "viewed_delivery_time")

    preferences = get_delivery_preferences(callback.from_user.id)

    text = "⏰ <b>Предпочтительное время доставки</b>\n\n"
    text += "Укажите удобное для вас время получения заказов. "
    text += "Мы постараемся учитывать ваши предпочтения при планировании доставки."

    await callback.message.edit_text(
        text,
        reply_markup=get_delivery_time_keyboard(preferences),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.DELIVERY_TIME_MENU)


@router.callback_query(F.data == "delivery_time:current")
async def show_current_delivery_time(callback: CallbackQuery):
    """Обработчик для кнопки 'Текущее время'"""
    preferences = get_delivery_preferences(callback.from_user.id)

    if preferences:
        text = f"Ваше текущее предпочтительное время доставки: {preferences['start_time']} - {preferences['end_time']}"
    else:
        text = "Вы еще не указали предпочтительное время доставки"

    await callback.answer(text, show_alert=True)


@router.callback_query(F.data == "delivery_time:back", StateFilter(AboutMeStates))
async def back_from_delivery_time(callback: CallbackQuery, state: FSMContext):
    """Возврат из времени доставки в главное меню"""
    await show_about_me_menu(callback, state)


@router.callback_query(F.data == "delivery_time:edit")
async def edit_delivery_time(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование времени доставки"""
    await callback.answer()

    log_user_action(callback.from_user.id, "started_editing_delivery_time")

    await callback.message.edit_text(
        "⏰ <b>Выберите начало интервала доставки:</b>",
        reply_markup=get_time_selection_keyboard("start"),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.SELECTING_START_TIME)


@router.callback_query(F.data.startswith("time_select:"), StateFilter(AboutMeStates.SELECTING_START_TIME))
async def process_start_time(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор начального времени"""
    await callback.answer()

    parts = callback.data.split(':')

    if parts[1] == "cancel":
        log_user_action(callback.from_user.id, "cancelled_editing_delivery_time", "at_start_time")
        await show_delivery_time(callback, state)
        return

    start_time = f"{parts[2]}:{parts[3]}"
    await state.update_data(start_time=start_time)

    await callback.message.edit_text(
        f"⏰ <b>Выберите конец интервала доставки:</b>\n"
        f"Начало: {start_time}",
        reply_markup=get_time_selection_keyboard("end", start_time),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.SELECTING_END_TIME)


@router.callback_query(F.data.startswith("time_select:"), StateFilter(AboutMeStates.SELECTING_END_TIME))
async def process_end_time(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор конечного времени"""
    parts = callback.data.split(':')

    if parts[1] == "cancel":
        await callback.answer()
        log_user_action(callback.from_user.id, "cancelled_editing_delivery_time", "at_end_time")
        await show_delivery_time(callback, state)
        return

    end_time = f"{parts[2]}:{parts[3]}"
    data = await state.get_data()
    start_time = data['start_time']

    if update_delivery_preferences(callback.from_user.id, start_time, end_time):
        await callback.answer("✅ Время доставки успешно обновлено!", show_alert=True)
        await show_delivery_time(callback, state)
    else:
        await callback.answer("❌ Ошибка при обновлении времени доставки", show_alert=True)


@router.callback_query(F.data.startswith("address:instructions_"))
async def edit_courier_instructions(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование инструкций для курьера"""
    await callback.answer()

    address_id = int(callback.data.split('_')[1])
    await state.update_data(editing_instructions_for_address=address_id)

    # Получаем текущие инструкции
    addresses = get_user_addresses(callback.from_user.id)
    address = next((addr for addr in addresses if addr['id'] == address_id), None)

    current_instructions = ""
    if address and address.get('courier_instructions'):
        current_instructions = f"\n\nТекущие инструкции:\n{address['courier_instructions']}"

    log_user_action(callback.from_user.id, "started_editing_courier_instructions", f"id:{address_id}")

    await callback.message.edit_text(
        f"📝 <b>Инструкции для курьера</b>\n\n"
        f"Укажите дополнительную информацию для курьера (код домофона, этаж, ориентиры и т.д.)\n"
        f"Максимум 150 символов.{current_instructions}",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.EDITING_COURIER_INSTRUCTIONS)


@router.message(StateFilter(AboutMeStates.EDITING_COURIER_INSTRUCTIONS))
async def process_courier_instructions(message: Message, state: FSMContext):
    """Обрабатывает введенные инструкции для курьера"""
    instructions = message.text.strip()

    # Проверка длины
    if len(instructions) > 150:
        await message.answer(
            f"❌ Инструкции слишком длинные ({len(instructions)}/150 символов).\n"
            "Пожалуйста, сократите текст:",
            reply_markup=get_skip_keyboard()
        )
        return

    data = await state.get_data()
    address_id = data['editing_instructions_for_address']

    if update_courier_instructions(address_id, message.from_user.id, instructions):
        await message.answer("✅", reply_markup=None)

        # Возвращаемся к деталям адреса
        addresses = get_user_addresses(message.from_user.id)
        address = next((addr for addr in addresses if addr['id'] == address_id), None)

        if address:
            text = f"📍 <b>Адрес доставки</b>\n\n"
            text += f"{address['address']}\n"

            if instructions:  # Используем новые инструкции
                text += f"\n📝 <b>Инструкции для курьера:</b>\n{instructions}\n"

            if address['is_default']:
                text += "\n⭐ <i>Основной адрес</i>"

            await message.answer(
                text,
                reply_markup=get_address_detail_keyboard(address_id, address['is_default']),
                parse_mode="HTML"
            )
            await state.set_state(AboutMeStates.ADDRESS_MENU)
    else:
        await message.answer("❌ Ошибка при сохранении инструкций. Попробуйте позже.")


@router.callback_query(F.data == "about_me:cancel_input", StateFilter(AboutMeStates))
async def cancel_input(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего ввода"""
    await callback.answer()

    current_state = await state.get_state()

    # Логируем отмену
    state_to_action = {
        AboutMeStates.EDITING_FIRST_NAME: "cancelled_editing_first_name",
        AboutMeStates.EDITING_LAST_NAME: "cancelled_editing_last_name",
        AboutMeStates.EDITING_BIRTH_DATE: "cancelled_editing_birth_date",
        AboutMeStates.EDITING_EMAIL: "cancelled_editing_email",
        AboutMeStates.EDITING_PHONE: "cancelled_editing_phone",
        AboutMeStates.ADDING_ADDRESS: "cancelled_adding_address",
        AboutMeStates.EDITING_ADDRESS: "cancelled_editing_address",
        AboutMeStates.EDITING_COURIER_INSTRUCTIONS: "cancelled_editing_courier_instructions"
    }

    if current_state in state_to_action:
        log_user_action(callback.from_user.id, state_to_action[current_state])

    # Определяем, куда вернуть пользователя
    if current_state in [AboutMeStates.EDITING_FIRST_NAME, AboutMeStates.EDITING_LAST_NAME,
                         AboutMeStates.EDITING_BIRTH_DATE, AboutMeStates.EDITING_EMAIL,
                         AboutMeStates.EDITING_PHONE]:
        await show_personal_info(callback, state)
    elif current_state in [AboutMeStates.ADDING_ADDRESS, AboutMeStates.EDITING_ADDRESS]:
        await show_addresses(callback, state)
    elif current_state == AboutMeStates.EDITING_COURIER_INSTRUCTIONS:
        # Возвращаем к деталям адреса
        data = await state.get_data()
        if 'editing_instructions_for_address' in data:
            callback.data = f"address:view_{data['editing_instructions_for_address']}"
            await view_address_detail(callback, state)
        else:
            await show_addresses(callback, state)
    else:
        await show_about_me_menu(callback, state)

# ==================== Общие обработчики ====================

@router.callback_query(F.data == "about_me:cancel_input", StateFilter(AboutMeStates))
async def cancel_input(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего ввода"""
    await callback.answer()

    current_state = await state.get_state()

    # Логируем отмену
    state_to_action = {
        AboutMeStates.EDITING_FIRST_NAME: "cancelled_editing_first_name",
        AboutMeStates.EDITING_LAST_NAME: "cancelled_editing_last_name",
        AboutMeStates.EDITING_BIRTH_DATE: "cancelled_editing_birth_date",
        AboutMeStates.EDITING_EMAIL: "cancelled_editing_email",
        AboutMeStates.EDITING_PHONE: "cancelled_editing_phone",
        AboutMeStates.ADDING_ADDRESS: "cancelled_adding_address",
        AboutMeStates.EDITING_ADDRESS: "cancelled_editing_address"
    }

    if current_state in state_to_action:
        log_user_action(callback.from_user.id, state_to_action[current_state])

    # Определяем, куда вернуть пользователя
    if current_state in [AboutMeStates.EDITING_FIRST_NAME, AboutMeStates.EDITING_LAST_NAME,
                         AboutMeStates.EDITING_BIRTH_DATE, AboutMeStates.EDITING_EMAIL,
                         AboutMeStates.EDITING_PHONE]:
        await show_personal_info(callback, state)
    elif current_state in [AboutMeStates.ADDING_ADDRESS, AboutMeStates.EDITING_ADDRESS]:
        await show_addresses(callback, state)
    else:
        await show_about_me_menu(callback, state)


@router.callback_query(F.data == "about_me:skip", StateFilter(AboutMeStates))
async def skip_input(callback: CallbackQuery, state: FSMContext):
    """Пропуск текущего ввода"""
    await callback.answer("Поле пропущено", show_alert=True)

    current_state = await state.get_state()

    # Логируем пропуск
    state_to_action = {
        AboutMeStates.EDITING_LAST_NAME: "skipped_last_name",
        AboutMeStates.EDITING_BIRTH_DATE: "skipped_birth_date",
        AboutMeStates.EDITING_EMAIL: "skipped_email",
        AboutMeStates.EDITING_PHONE: "skipped_phone",
        AboutMeStates.EDITING_COURIER_INSTRUCTIONS: "skipped_courier_instructions"
    }

    if current_state in state_to_action:
        log_user_action(callback.from_user.id, state_to_action[current_state])

    # Возвращаем к соответствующему меню
    if current_state in [AboutMeStates.EDITING_LAST_NAME, AboutMeStates.EDITING_BIRTH_DATE,
                         AboutMeStates.EDITING_EMAIL, AboutMeStates.EDITING_PHONE]:
        await show_personal_info(callback, state)
    elif current_state == AboutMeStates.EDITING_COURIER_INSTRUCTIONS:
        data = await state.get_data()
        if 'editing_instructions_for_address' in data:
            # Очищаем инструкции, если были
            update_courier_instructions(data['editing_instructions_for_address'], callback.from_user.id, "")
            callback.data = f"address:view_{data['editing_instructions_for_address']}"
            await view_address_detail(callback, state)
        else:
            await show_addresses(callback, state)


# ==================== Вспомогательные функции ====================

async def show_personal_info_message(message: Message, state: FSMContext):
    """Показывает меню личных данных через обычное сообщение"""
    user_info = get_user_personal_info(message.from_user.id)

    text = "👤 <b>Личные данные</b>\n\n"
    text += "Нажмите на поле для редактирования:"

    await message.answer(
        text,
        reply_markup=get_personal_info_keyboard(user_info),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.PERSONAL_INFO_MENU)


async def show_addresses_message(message: Message, state: FSMContext):
    """Показывает список адресов через обычное сообщение"""
    addresses = get_user_addresses(message.from_user.id)

    text = "📍 <b>Адреса доставки</b>\n\n"
    if addresses:
        text += "Ваши сохраненные адреса:\n\n"
        for i, addr in enumerate(addresses, 1):
            default_mark = " ⭐" if addr['is_default'] else ""
            text += f"{i}. {addr['address']}{default_mark}\n"
    else:
        text += "У вас пока нет сохраненных адресов."

    await message.answer(
        text,
        reply_markup=get_addresses_keyboard(addresses),
        parse_mode="HTML"
    )
    await state.set_state(AboutMeStates.ADDRESS_MENU)
