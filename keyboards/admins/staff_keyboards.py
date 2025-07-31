from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict


def get_staff_management_keyboard() -> InlineKeyboardMarkup:
    """Главное меню управления персоналом"""
    keyboard = [
        [InlineKeyboardButton(text="🔎 Просмотр сотрудников", callback_data="staff_view")],
        [InlineKeyboardButton(text="➕ Добавить сотрудника", callback_data="staff_add")],
        [InlineKeyboardButton(text="🆕 Создать новый статус", callback_data="staff_create_status")],  # Новая кнопка
        [InlineKeyboardButton(text="🔙 Назад в меню администратора", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_staff_roles_keyboard(roles: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура выбора роли для фильтрации"""
    keyboard = []
    for role in roles:
        keyboard.append([InlineKeyboardButton(text=role, callback_data=f"staff_role_{role}")])

    keyboard.append([InlineKeyboardButton(text="🌐 Показать всех сотрудников", callback_data="staff_all")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="staff_management")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_staff_list_keyboard(staff_list: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура со списком сотрудников"""
    keyboard = []

    for staff in staff_list:
        name = f"{staff['first_name']} {staff['last_name'] or ''}".strip()
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"staff_id_{staff['id']}")])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад к ролям", callback_data="staff_view")])
    keyboard.append([InlineKeyboardButton(text="👥 Меню управления персоналом", callback_data="staff_management")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_staff_detail_keyboard(staff_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура для управления конкретным сотрудником"""
    status_text = "Заблокировать" if is_active else "Разблокировать"

    keyboard = [
        [InlineKeyboardButton(text="Изменить роль", callback_data=f"staff_change_role_{staff_id}")],
        [InlineKeyboardButton(text="Изменить уровень доступа", callback_data=f"staff_change_access_{staff_id}")],
        [InlineKeyboardButton(text=status_text, callback_data=f"staff_toggle_status_{staff_id}")],
        [InlineKeyboardButton(text="Удалить сотрудника", callback_data=f"staff_delete_{staff_id}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="staff_view")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_role_selection_keyboard(roles: List[str], callback_prefix: str = "staff_select_role") -> InlineKeyboardMarkup:
    """Клавиатура для выбора роли"""
    keyboard = []

    for role in roles:
        keyboard.append([InlineKeyboardButton(text=role, callback_data=f"{callback_prefix}_{role}")])

    keyboard.append([InlineKeyboardButton(text="Отменить добавление", callback_data="staff_cancel")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(action: str, staff_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения действий"""
    callback_yes = f"staff_confirm_{action}"
    if staff_id:
        callback_yes += f"_{staff_id}"

    keyboard = [
        [InlineKeyboardButton(text="✅ Да, подтверждаю", callback_data=callback_yes)],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="staff_cancel")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой пропуска шага"""
    keyboard = [
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data="staff_skip")],
        [InlineKeyboardButton(text="Отменить добавление", callback_data="staff_cancel")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_staff_statuses_keyboard(statuses: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура со списком статусов (ролей) сотрудников"""
    keyboard = []

    for status in statuses:
        keyboard.append([InlineKeyboardButton(text=status, callback_data=f"staff_status_view_{status}")])

    keyboard.append([InlineKeyboardButton(text="Создать новый статус", callback_data="staff_create_status")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="staff_management")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура только с кнопкой отмены"""
    keyboard = [
        [InlineKeyboardButton(text="Отменить добавление", callback_data="staff_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_keyboard_create_status() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой отмены"""
    keyboard = [
        [InlineKeyboardButton(text="Отменить создание", callback_data="staff_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_description_step_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками пропуска и отмены для шага описания"""
    keyboard = [
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data="staff_skip_description")],
        [InlineKeyboardButton(text="Отменить", callback_data="staff_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
