from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Optional


def get_about_me_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню раздела 'О себе'"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="👤 Личные данные",
        callback_data="about_me:personal_info"
    ))

    builder.row(InlineKeyboardButton(
        text="📍 Адреса доставки",
        callback_data="about_me:addresses"
    ))

    builder.row(InlineKeyboardButton(
        text="⏰ Время доставки",
        callback_data="about_me:delivery_time"
    ))

    builder.row(InlineKeyboardButton(
        text="🔒 О безопасности данных",
        callback_data="about_me:data_security"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад в профиль",
        callback_data="about_me:back_to_profile"
    ))

    return builder.as_markup()


def get_personal_info_keyboard(user_info: Optional[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура меню личных данных"""
    builder = InlineKeyboardBuilder()

    first_name = user_info.get('first_name', 'Не указано') if user_info else 'Не указано'
    last_name = user_info.get('last_name', 'Не указано') if user_info else 'Не указано'
    birth_date = user_info.get('birth_date', 'Не указана') if user_info else 'Не указана'
    gender = user_info.get('gender', 'Не указан') if user_info else 'Не указан'
    email = user_info.get('email', 'Не указан') if user_info else 'Не указан'
    phone = user_info.get('phone', 'Не указан') if user_info else 'Не указан'

    builder.row(InlineKeyboardButton(
        text=f"Имя: {first_name}",
        callback_data="personal:edit_first_name"
    ))

    builder.row(InlineKeyboardButton(
        text=f"Фамилия: {last_name}",
        callback_data="personal:edit_last_name"
    ))

    builder.row(InlineKeyboardButton(
        text=f"📅 Дата рождения: {birth_date}",
        callback_data="personal:edit_birth_date"
    ))

    builder.row(InlineKeyboardButton(
        text=f"👤 Пол: {gender}",
        callback_data="personal:edit_gender"
    ))

    builder.row(InlineKeyboardButton(
        text=f"📧 Email: {email}",
        callback_data="personal:edit_email"
    ))

    builder.row(InlineKeyboardButton(
        text=f"📱 Телефон: {phone}",
        callback_data="personal:edit_phone"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="personal:back"
    ))

    return builder.as_markup()


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора пола"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="👨 Мужской", callback_data="gender:male"),
        InlineKeyboardButton(text="👩 Женский", callback_data="gender:female")
    )

    builder.row(InlineKeyboardButton(
        text="🚫 Не указывать",
        callback_data="gender:skip"
    ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="gender:cancel"
    ))

    return builder.as_markup()


def get_addresses_keyboard(addresses: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура списка адресов"""
    builder = InlineKeyboardBuilder()

    if addresses:
        for i, addr in enumerate(addresses, 1):
            default_mark = " ⭐" if addr['is_default'] else ""
            text = f"📍 Адрес {i}{default_mark}"

            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"address:view_{addr['id']}"
            ))

    builder.row(InlineKeyboardButton(
        text="➕ Добавить адрес",
        callback_data="address:add_new"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="address:back"
    ))

    return builder.as_markup()


def get_address_detail_keyboard(address_id: int, is_default: bool) -> InlineKeyboardMarkup:
    """Клавиатура детальной информации об адресе"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="✏️ Изменить адрес",
        callback_data=f"address:edit_{address_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="📝 Инструкции для курьера",
        callback_data=f"address:instructions_{address_id}"
    ))

    if not is_default:
        builder.row(InlineKeyboardButton(
            text="⭐ Сделать основным",
            callback_data=f"address:set_default_{address_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="🗑 Удалить",
        callback_data=f"address:delete_{address_id}"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 К списку адресов",
        callback_data="address:list"
    ))

    return builder.as_markup()


def get_delivery_time_keyboard(preferences: Optional[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура настройки времени доставки"""
    builder = InlineKeyboardBuilder()

    if preferences:
        current_time = f"{preferences['start_time']} - {preferences['end_time']}"
    else:
        current_time = "Не указано"

    builder.row(InlineKeyboardButton(
        text=f"⏰ Текущее время: {current_time}",
        callback_data="delivery_time:current"
    ))

    builder.row(InlineKeyboardButton(
        text="✏️ Изменить время",
        callback_data="delivery_time:edit"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="delivery_time:back"
    ))

    return builder.as_markup()


def get_time_selection_keyboard(time_type: str, start_time: str = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени"""
    builder = InlineKeyboardBuilder()

    all_times = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00",
                 "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00"]

    # Если выбираем конечное время, фильтруем по начальному
    if time_type == "end" and start_time:
        start_hour = int(start_time.split(':')[0])
        times = [t for t in all_times if int(t.split(':')[0]) > start_hour]
    else:
        times = all_times

    for i in range(0, len(times), 3):
        row_buttons = []
        for j in range(3):
            if i + j < len(times):
                time = times[i + j]
                row_buttons.append(InlineKeyboardButton(
                    text=time,
                    callback_data=f"time_select:{time_type}:{time}"
                ))
        builder.row(*row_buttons)

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="time_select:cancel"
    ))

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="about_me:cancel_input"
    ))

    return builder.as_markup()


def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками пропустить и отменить"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить", callback_data="about_me:skip"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="about_me:cancel_input")
    )

    return builder.as_markup()
