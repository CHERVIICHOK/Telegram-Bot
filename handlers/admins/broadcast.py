import asyncio
import json
from typing import Dict
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramRetryAfter

from database.admins.users_db import get_all_users, get_active_users, get_user_regions, count_users
from database.admins.broadcast_db import (
    ensure_broadcast_tables, get_broadcast_templates,
    get_broadcast_template, start_broadcast, update_broadcast_status,
    get_broadcast_history, get_broadcast_details
)
from filters.admin_filter import AdminFilter
from keyboards.admins.broadcast_keyboards import (
    get_broadcast_menu_keyboard, get_broadcast_type_keyboard,
    get_target_selection_keyboard, get_time_selection_keyboard,
    get_active_users_period_keyboard, get_regions_keyboard,
    get_templates_keyboard, get_broadcast_preview_keyboard,
    get_broadcast_history_keyboard, get_broadcast_history_list_keyboard,
    get_confirm_cancel_keyboard, get_back_keyboard
)
from utils.broadcast_utils import (
    parse_button_data, validate_buttons_format,
    format_broadcast_preview,
    format_broadcast_details, parse_scheduled_time
)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

# Убедимся, что таблицы для рассылок существуют
ensure_broadcast_tables()


# Состояния для FSM
class BroadcastStates(StatesGroup):
    selecting_type = State()
    entering_text = State()
    uploading_media = State()
    selecting_target = State()
    selecting_active_period = State()
    selecting_region = State()
    selecting_time = State()
    entering_scheduled_time = State()
    editing_buttons = State()
    entering_button_text = State()
    entering_button_url = State()
    preview = State()

    template_naming = State()
    template_selecting = State()


# Глобальные переменные для хранения состояния
BROADCAST_DATA = {}  # user_id -> broadcast_data
TEMP_BUTTONS = {}  # user_id -> [buttons]
REGIONS_CACHE = {}  # Кеш регионов для уменьшения обращений к БД
TEMPLATES_CACHE = {}  # Кеш шаблонов
CURRENT_PAGE = {}  # user_id -> page


# Обработчики команд
@router.callback_query(F.data == "send_broadcast")
async def cmd_broadcast(callback: CallbackQuery):
    """Обработчик для кнопки создания рассылки"""
    await callback.message.edit_text(
        "📨 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_broadcast_menu_keyboard(),
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


@router.callback_query(F.data == "back_to_broadcast_menu")
async def cmd_back_to_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик для возврата в меню рассылок"""
    await state.clear()

    user_id = callback.from_user.id
    if user_id in BROADCAST_DATA:
        del BROADCAST_DATA[user_id]

    await cmd_broadcast(callback)


# Создание рассылки
@router.callback_query(F.data == "create_broadcast")
async def cmd_create_broadcast(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала создания рассылки"""
    user_id = callback.from_user.id

    # Инициализируем данные рассылки
    BROADCAST_DATA[user_id] = {
        "type": "text",
        "text": "",
        "media_type": None,
        "media_file": None,
        "buttons": [],
        "target_type": "all",
        "total_recipients": 0
    }

    await callback.message.edit_text(
        "📤 <b>Создание новой рассылки</b>\n\n"
        "Выберите тип сообщения:",
        reply_markup=get_broadcast_type_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_type)
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_type:"), BroadcastStates.selecting_type)
async def process_broadcast_type(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора типа рассылки"""
    user_id = callback.from_user.id
    _, message_type = callback.data.split(":", 1)

    BROADCAST_DATA[user_id]["type"] = message_type

    await callback.message.edit_text(
        "📝 <b>Введите текст сообщения:</b>\n\n"
        "Вы можете использовать HTML-разметку для форматирования текста.\n"
        "Например: <b>жирный</b>, <i>курсив</i>, <a href='https://example.com'>ссылка</a>",
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.entering_text)
    await callback.answer()


@router.callback_query(F.data == "broadcast_use_template", BroadcastStates.selecting_type)
async def process_use_template(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора использования шаблона"""
    user_id = callback.from_user.id

    # Получаем шаблоны из базы данных
    templates = get_broadcast_templates()
    TEMPLATES_CACHE[user_id] = templates

    if not templates:
        await callback.message.edit_text(
            "📝 <b>Шаблоны не найдены</b>\n\n"
            "У вас пока нет сохраненных шаблонов. Создайте новую рассылку.",
            reply_markup=get_back_keyboard("back_to_broadcast_type"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📑 <b>Выберите шаблон рассылки:</b>",
            reply_markup=get_templates_keyboard(templates),
            parse_mode="HTML"
        )

        await state.set_state(BroadcastStates.template_selecting)

    await callback.answer()


@router.callback_query(F.data.startswith("select_template:"), BroadcastStates.template_selecting)
async def process_template_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора шаблона"""
    user_id = callback.from_user.id
    _, template_id = callback.data.split(":", 1)

    template = get_broadcast_template(int(template_id))

    if not template:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Выбранный шаблон не найден. Попробуйте выбрать другой шаблон.",
            reply_markup=get_back_keyboard("broadcast_use_template"),
            parse_mode="HTML"
        )
    else:
        # Заполняем данные рассылки из шаблона
        _, name, content, msg_type, buttons_json, _ = template

        try:
            buttons = json.loads(buttons_json) if buttons_json else []
        except json.JSONDecodeError:
            buttons = []

        BROADCAST_DATA[user_id] = {
            "type": msg_type,
            "text": content,
            "media_type": "photo" if msg_type == "photo" else None,
            "media_file": None,  # Медиафайл нужно будет загрузить заново
            "buttons": buttons,
            "target_type": "all",
            "total_recipients": 0
        }

        if msg_type == "photo":
            await callback.message.edit_text(
                "🖼 <b>Загрузите изображение</b>\n\n"
                "Отправьте фотографию, которую хотите использовать в рассылке.",
                parse_mode="HTML"
            )
            await state.set_state(BroadcastStates.uploading_media)
        else:
            # Переходим к выбору целевой аудитории
            await callback.message.edit_text(
                "👥 <b>Выберите целевую аудиторию:</b>",
                reply_markup=get_target_selection_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(BroadcastStates.selecting_target)

    await callback.answer()


@router.message(BroadcastStates.entering_text)
async def process_broadcast_text(message: Message, state: FSMContext, bot: Bot):
    """Обработчик ввода текста рассылки"""
    user_id = message.from_user.id

    if not message.text or not message.text.strip():
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Текст сообщения не может быть пустым. Пожалуйста, введите текст:",
            parse_mode="HTML"
        )
        return

    BROADCAST_DATA[user_id]["text"] = message.text

    if BROADCAST_DATA[user_id]["type"] == "photo":
        await message.answer(
            "🖼 <b>Загрузите изображение</b>\n\n"
            "Отправьте фотографию, которую хотите использовать в рассылке.",
            parse_mode="HTML"
        )
        await state.set_state(BroadcastStates.uploading_media)
    else:
        # Для текстовой рассылки переходим к выбору целевой аудитории
        await message.answer(
            "👥 <b>Выберите целевую аудиторию:</b>",
            reply_markup=get_target_selection_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(BroadcastStates.selecting_target)


@router.message(BroadcastStates.uploading_media)
async def process_broadcast_media(message: Message, state: FSMContext):
    """Обработчик загрузки медиафайла для рассылки"""
    user_id = message.from_user.id

    if not message.photo:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Пожалуйста, отправьте фотографию. Текстовые сообщения или другие типы файлов не поддерживаются.",
            parse_mode="HTML"
        )
        return

    # Сохраняем идентификатор файла для последующего использования
    file_id = message.photo[-1].file_id
    BROADCAST_DATA[user_id]["media_file"] = file_id
    BROADCAST_DATA[user_id]["media_type"] = "photo"

    await message.answer(
        "👥 <b>Выберите целевую аудиторию:</b>",
        reply_markup=get_target_selection_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_target)


@router.callback_query(F.data == "back_to_broadcast_type")
async def cmd_back_to_broadcast_type(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору типа рассылки"""
    await callback.message.edit_text(
        "📤 <b>Создание новой рассылки</b>\n\n"
        "Выберите тип сообщения:",
        reply_markup=get_broadcast_type_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_type)
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_target:"), BroadcastStates.selecting_target)
async def process_target_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора целевой аудитории"""
    user_id = callback.from_user.id
    _, target_type = callback.data.split(":", 1)

    BROADCAST_DATA[user_id]["target_type"] = target_type

    if target_type == "all":
        # Получаем общее количество пользователей
        total_users = count_users()
        BROADCAST_DATA[user_id]["total_recipients"] = total_users

        await callback.message.edit_text(
            "⏰ <b>Выберите время отправки:</b>",
            reply_markup=get_time_selection_keyboard(),
            parse_mode="HTML"
        )

        await state.set_state(BroadcastStates.selecting_time)

    elif target_type == "active":
        await callback.message.edit_text(
            "📊 <b>Выберите период активности:</b>\n\n"
            "За какой период учитывать активность пользователей?",
            reply_markup=get_active_users_period_keyboard(),
            parse_mode="HTML"
        )

        await state.set_state(BroadcastStates.selecting_active_period)

    elif target_type == "region":
        # Получаем список регионов из базы данных
        regions_dict = get_user_regions()
        regions = list(regions_dict.keys())
        REGIONS_CACHE[user_id] = regions_dict

        if not regions:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                "В базе данных нет информации о регионах пользователей.",
                reply_markup=get_back_keyboard("back_to_broadcast_target"),
                parse_mode="HTML"
            )
            return

        CURRENT_PAGE[user_id] = 1

        await callback.message.edit_text(
            "🌍 <b>Выберите регион:</b>",
            reply_markup=get_regions_keyboard(regions),
            parse_mode="HTML"
        )

        await state.set_state(BroadcastStates.selecting_region)

    await callback.answer()


@router.callback_query(F.data == "back_to_broadcast_target")
async def cmd_back_to_broadcast_target(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору целевой аудитории"""
    await callback.message.edit_text(
        "👥 <b>Выберите целевую аудиторию:</b>",
        reply_markup=get_target_selection_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_target)
    await callback.answer()


@router.callback_query(F.data.startswith("active_period:"), BroadcastStates.selecting_active_period)
async def process_active_period(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода активности"""
    user_id = callback.from_user.id
    _, days = callback.data.split(":", 1)
    days = int(days)

    # Получаем активных пользователей за выбранный период
    active_users = get_active_users(days)

    BROADCAST_DATA[user_id]["active_days"] = days
    BROADCAST_DATA[user_id]["total_recipients"] = len(active_users)

    await callback.message.edit_text(
        f"⏰ <b>Выберите время отправки:</b>\n\n"
        f"Выбрано получателей: {len(active_users)}",
        reply_markup=get_time_selection_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_time)
    await callback.answer()


@router.callback_query(F.data.startswith("regions_page:"), BroadcastStates.selecting_region)
async def process_regions_page(callback: CallbackQuery):
    """Обработчик пагинации списка регионов"""
    user_id = callback.from_user.id
    _, page = callback.data.split(":", 1)
    page = int(page)

    CURRENT_PAGE[user_id] = page

    regions = list(REGIONS_CACHE[user_id].keys())

    await callback.message.edit_text(
        "🌍 <b>Выберите регион:</b>",
        reply_markup=get_regions_keyboard(regions, page),
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data.startswith("select_region:"), BroadcastStates.selecting_region)
async def process_region_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора региона"""
    user_id = callback.from_user.id
    _, region = callback.data.split(":", 1)

    # Получаем пользователей выбранного региона
    users_in_region = REGIONS_CACHE[user_id].get(region, [])

    BROADCAST_DATA[user_id]["region"] = region
    BROADCAST_DATA[user_id]["total_recipients"] = len(users_in_region)

    await callback.message.edit_text(
        f"⏰ <b>Выберите время отправки:</b>\n\n"
        f"Выбран регион: {region}\n"
        f"Количество получателей: {len(users_in_region)}",
        reply_markup=get_time_selection_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_time)
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_time:"), BroadcastStates.selecting_time)
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора времени отправки"""
    user_id = callback.from_user.id
    _, time_option = callback.data.split(":", 1)

    if time_option == "now":
        # Отправка сейчас - переходим к предпросмотру
        await show_broadcast_preview(callback.message, user_id, state)
    elif time_option == "schedule":
        # Запланированная отправка - запрашиваем время
        await callback.message.edit_text(
            "⏰ <b>Введите время для отправки:</b>\n\n"
            "Формат: ЧЧ:ММ (например, 15:30) для отправки сегодня\n"
            "или ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2023 15:30) для конкретной даты",
            reply_markup=get_back_keyboard("back_to_broadcast_time"),
            parse_mode="HTML"
        )

        await state.set_state(BroadcastStates.entering_scheduled_time)

    await callback.answer()


@router.callback_query(F.data == "back_to_broadcast_time")
async def cmd_back_to_broadcast_time(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору времени отправки"""
    await callback.message.edit_text(
        "⏰ <b>Выберите время отправки:</b>",
        reply_markup=get_time_selection_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.selecting_time)
    await callback.answer()


@router.message(BroadcastStates.entering_scheduled_time)
async def process_scheduled_time(message: Message, state: FSMContext):
    """Обработчик ввода запланированного времени отправки"""
    user_id = message.from_user.id
    time_string = message.text.strip()

    scheduled_time = parse_scheduled_time(time_string)

    if not scheduled_time:
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Неверный формат времени. Пожалуйста, используйте один из форматов:\n"
            "- ЧЧ:ММ (например, 15:30) для отправки сегодня\n"
            "- ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2023 15:30) для конкретной даты",
            reply_markup=get_back_keyboard("back_to_broadcast_time"),
            parse_mode="HTML"
        )
        return

    # Проверяем, что выбранное время в будущем
    if scheduled_time <= datetime.now():
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Выбранное время уже прошло. Пожалуйста, выберите время в будущем.",
            reply_markup=get_back_keyboard("back_to_broadcast_time"),
            parse_mode="HTML"
        )
        return

    BROADCAST_DATA[user_id]["scheduled_time"] = scheduled_time.strftime("%Y-%m-%d %H:%M:%S")

    # Переходим к предпросмотру
    await show_broadcast_preview(message, user_id, state)


async def show_broadcast_preview(message, user_id, state):
    """Показывает предпросмотр рассылки"""
    broadcast_data = BROADCAST_DATA[user_id]

    # Устанавливаем состояние предпросмотра
    await state.set_state(BroadcastStates.preview)

    # Генерируем текст предпросмотра
    preview_text = format_broadcast_preview(broadcast_data)

    # Генерируем клавиатуру для предпросмотра
    has_buttons = bool(broadcast_data.get("buttons", []))
    keyboard = get_broadcast_preview_keyboard(has_buttons, broadcast_data.get("buttons", []))

    # Показываем предпросмотр
    if broadcast_data.get("media_type") == "photo" and broadcast_data.get("media_file"):
        # Предпросмотр с фото
        await message.answer_photo(
            photo=broadcast_data["media_file"],
            caption=preview_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        # Текстовый предпросмотр
        await message.edit_text(
            preview_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data == "edit_broadcast_text", BroadcastStates.preview)
async def cmd_edit_broadcast_text(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования текста рассылки"""
    await callback.message.edit_text(
        "📝 <b>Введите новый текст сообщения:</b>\n\n"
        "Вы можете использовать HTML-разметку для форматирования текста.",
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.entering_text)
    await callback.answer()


@router.callback_query(F.data.startswith("add_broadcast_buttons"), BroadcastStates.preview)
async def cmd_add_broadcast_buttons(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления кнопок к рассылке"""
    user_id = callback.from_user.id

    # Инициализируем временное хранилище для кнопок
    TEMP_BUTTONS[user_id] = []

    await callback.message.edit_text(
        "🔘 <b>Добавление кнопок</b>\n\n"
        "Отправьте кнопки в формате:\n"
        "<code>Текст кнопки|https://example.com</code>\n\n"
        "Каждая кнопка должна быть на отдельной строке.\n"
        "Пример:\n"
        "<code>Наш сайт|https://example.com\n"
        "Наш канал|https://t.me/example</code>",
        reply_markup=get_back_keyboard("back_to_preview"),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.editing_buttons)
    await callback.answer()


@router.callback_query(F.data == "edit_broadcast_buttons", BroadcastStates.preview)
async def cmd_edit_broadcast_buttons(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования кнопок рассылки"""
    user_id = callback.from_user.id
    buttons = BROADCAST_DATA[user_id].get("buttons", [])

    # Преобразуем кнопки в текстовый формат для редактирования
    buttons_text = ""
    for button in buttons:
        if "text" in button and "url" in button:
            buttons_text += f"{button['text']}|{button['url']}\n"

    await callback.message.edit_text(
        "🔘 <b>Редактирование кнопок</b>\n\n"
        "Отредактируйте кнопки в формате:\n"
        "<code>Текст кнопки|https://example.com</code>\n\n"
        "Каждая кнопка должна быть на отдельной строке.\n"
        "Текущие кнопки:\n\n"
        f"<code>{buttons_text}</code>",
        reply_markup=get_back_keyboard("back_to_preview"),
        parse_mode="HTML"
    )

    await state.set_state(BroadcastStates.editing_buttons)
    await callback.answer()


@router.callback_query(F.data == "back_to_preview", BroadcastStates.editing_buttons)
async def cmd_back_to_preview(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к предпросмотру рассылки"""
    user_id = callback.from_user.id

    # Очищаем временные данные кнопок, если они есть
    if user_id in TEMP_BUTTONS:
        del TEMP_BUTTONS[user_id]

    # Возвращаемся к предпросмотру
    await show_broadcast_preview(callback.message, user_id, state)
    await callback.answer()


@router.message(BroadcastStates.editing_buttons)
async def process_buttons_edit(message: Message, state: FSMContext):
    """Обработчик ввода кнопок"""
    user_id = message.from_user.id
    buttons_text = message.text.strip()

    # Проверяем формат кнопок
    is_valid, error_message = validate_buttons_format(buttons_text)

    if not is_valid:
        await message.answer(
            f"❌ <b>Ошибка в формате кнопок</b>\n\n"
            f"{error_message}\n\n"
            f"Пожалуйста, исправьте ошибку и отправьте кнопки снова.",
            reply_markup=get_back_keyboard("back_to_preview"),
            parse_mode="HTML"
        )
        return

    # Парсим кнопки
    buttons = parse_button_data(buttons_text)

    # Сохраняем кнопки
    BROADCAST_DATA[user_id]["buttons"] = buttons

    # Возвращаемся к предпросмотру
    await show_broadcast_preview(message, user_id, state)


@router.callback_query(F.data == "confirm_broadcast", BroadcastStates.preview)
async def cmd_confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик подтверждения отправки рассылки"""
    user_id = callback.from_user.id
    broadcast_data = BROADCAST_DATA[user_id]

    # Запрашиваем подтверждение перед отправкой
    recipients_count = broadcast_data.get("total_recipients", 0)

    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение отправки</b>\n\n"
        f"Вы собираетесь отправить рассылку {recipients_count} пользователям.\n"
        f"Вы уверены?",
        reply_markup=get_confirm_cancel_keyboard("start_sending", "cancel_sending"),
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data == "start_sending")
async def cmd_start_sending(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик начала отправки рассылки"""
    user_id = callback.from_user.id
    broadcast_data = BROADCAST_DATA.get(user_id, {})

    if not broadcast_data:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Данные рассылки не найдены. Пожалуйста, создайте рассылку заново.",
            reply_markup=get_broadcast_menu_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return

    # Сохраняем рассылку в базу данных
    broadcast_id = start_broadcast(broadcast_data)

    if broadcast_id == -1:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не удалось создать рассылку. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_broadcast_menu_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return

    # Если указано запланированное время, сообщаем об этом
    if "scheduled_time" in broadcast_data:
        scheduled_time = broadcast_data["scheduled_time"]
        await callback.message.edit_text(
            f"✅ <b>Рассылка #{broadcast_id} запланирована</b>\n\n"
            f"Рассылка будет отправлена {scheduled_time}.",
            reply_markup=get_broadcast_menu_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()

        # TODO: Здесь должна быть логика для планирования отправки
        # Например, через задачи Celery или другой планировщик
        return

    # Начинаем отправку рассылки
    await callback.message.edit_text(
        f"🚀 <b>Рассылка #{broadcast_id} запущена</b>\n\n"
        f"Идет отправка сообщений...",
        reply_markup=get_broadcast_menu_keyboard(),
        parse_mode="HTML"
    )

    # Очищаем состояние и данные рассылки
    await state.clear()
    if user_id in BROADCAST_DATA:
        del BROADCAST_DATA[user_id]

    await callback.answer()

    # Запускаем отправку в фоновом режиме
    asyncio.create_task(send_broadcast(bot, broadcast_id, broadcast_data))


async def send_broadcast(bot: Bot, broadcast_id: int, broadcast_data: Dict):
    """Отправляет рассылку пользователям"""
    target_type = broadcast_data.get("target_type", "all")

    # Получаем список получателей
    if target_type == "all":
        users = get_all_users()
        recipients = [user[0] for user in users]  # user_id - первый элемент кортежа
    elif target_type == "active":
        days = broadcast_data.get("active_days", 30)
        recipients = get_active_users(days)
    elif target_type == "region":
        region = broadcast_data.get("region", "")
        regions_dict = get_user_regions()
        recipients = regions_dict.get(region, [])
    else:
        recipients = []

    # Обновляем статус рассылки
    update_broadcast_status(broadcast_id, "pending", 0)

    # Подготавливаем данные для отправки
    text = broadcast_data.get("text", "")
    media_type = broadcast_data.get("media_type")
    media_file = broadcast_data.get("media_file")
    buttons = broadcast_data.get("buttons", [])

    # Создаем клавиатуру, если есть кнопки
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    markup = None
    if buttons:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button["text"], url=button["url"])]
            for button in buttons
        ])

    # Счетчик успешно отправленных сообщений
    sent_count = 0

    # Отправляем сообщения
    for user_id in recipients:
        try:
            if media_type == "photo" and media_file:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=media_file,
                    caption=text,
                    reply_markup=markup
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=markup
                )

            sent_count += 1

            # Обновляем прогресс каждые 10 сообщений
            if sent_count % 10 == 0:
                update_broadcast_status(broadcast_id, "pending", sent_count)

            # Задержка для избежания ограничений Telegram
            await asyncio.sleep(0.05)

        except TelegramRetryAfter as e:
            # При превышении лимита ждем указанное время
            await asyncio.sleep(e.retry_after)

            # Повторная попытка отправки
            try:
                if media_type == "photo" and media_file:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=media_file,
                        caption=text,
                        reply_markup=markup
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=markup
                    )

                sent_count += 1
            except Exception:
                continue

        except Exception as e:
            # Игнорируем другие ошибки и продолжаем
            print(f"Ошибка при отправке рассылки пользователю {user_id}: {e}")
            continue

    # Обновляем статус рассылки как завершенную
    update_broadcast_status(broadcast_id, "completed", sent_count)


@router.callback_query(F.data == "cancel_sending")
async def cmd_cancel_sending(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены отправки рассылки"""
    await callback.message.edit_text(
        "❌ <b>Отправка рассылки отменена</b>",
        reply_markup=get_broadcast_menu_keyboard(),
        parse_mode="HTML"
    )

    # Очищаем состояние и данные рассылки
    await state.clear()
    user_id = callback.from_user.id
    if user_id in BROADCAST_DATA:
        del BROADCAST_DATA[user_id]

    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cmd_cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены создания рассылки"""
    await callback.message.edit_text(
        "❌ <b>Создание рассылки отменено</b>",
        reply_markup=get_broadcast_menu_keyboard(),
        parse_mode="HTML"
    )

    # Очищаем состояние и данные рассылки
    await state.clear()
    user_id = callback.from_user.id
    if user_id in BROADCAST_DATA:
        del BROADCAST_DATA[user_id]

    await callback.answer()


# Работа с шаблонами рассылок
@router.callback_query(F.data == "broadcast_templates")
async def cmd_broadcast_templates(callback: CallbackQuery, state: FSMContext):
    """Обработчик просмотра шаблонов рассылок"""
    user_id = callback.from_user.id

    # Получаем шаблоны из базы данных
    templates = get_broadcast_templates()
    TEMPLATES_CACHE[user_id] = templates

    if not templates:
        await callback.message.edit_text(
            "📝 <b>Шаблоны не найдены</b>\n\n"
            "У вас пока нет сохраненных шаблонов. Вы можете создать новый шаблон.",
            reply_markup=get_back_keyboard("back_to_broadcast_menu"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📑 <b>Шаблоны рассылок</b>\n\n"
            "Выберите шаблон для просмотра или создайте новый:",
            reply_markup=get_templates_keyboard(templates),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "create_new_template")
async def cmd_create_new_template(callback: CallbackQuery, state: FSMContext):
    """Обработчик создания нового шаблона"""
    # Перенаправляем на создание рассылки
    await cmd_create_broadcast(callback, state)


@router.callback_query(F.data.startswith("templates_page:"))
async def cmd_templates_page(callback: CallbackQuery):
    """Обработчик пагинации списка шаблонов"""
    user_id = callback.from_user.id
    _, page = callback.data.split(":", 1)
    page = int(page)

    templates = TEMPLATES_CACHE.get(user_id, [])

    await callback.message.edit_text(
        "📑 <b>Шаблоны рассылок</b>\n\n"
        "Выберите шаблон для просмотра или создайте новый:",
        reply_markup=get_templates_keyboard(templates, page),
        parse_mode="HTML"
    )

    await callback.answer()


# История рассылок
@router.callback_query(F.data == "broadcast_history")
async def cmd_broadcast_history(callback: CallbackQuery):
    """Обработчик просмотра истории рассылок"""
    user_id = callback.from_user.id

    # Получаем историю рассылок из базы данных
    broadcasts = get_broadcast_history()

    if not broadcasts:
        await callback.message.edit_text(
            "📝 <b>История рассылок пуста</b>\n\n"
            "У вас пока нет отправленных рассылок.",
            reply_markup=get_back_keyboard("back_to_broadcast_menu"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📊 <b>История рассылок</b>\n\n"
            "Выберите рассылку для просмотра деталей:",
            reply_markup=get_broadcast_history_list_keyboard(broadcasts),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("history_page:"))
async def cmd_history_page(callback: CallbackQuery):
    """Обработчик пагинации истории рассылок"""
    _, page = callback.data.split(":", 1)
    page = int(page)

    # Получаем историю рассылок из базы данных
    broadcasts = get_broadcast_history()

    await callback.message.edit_text(
        "📊 <b>История рассылок</b>\n\n"
        "Выберите рассылку для просмотра деталей:",
        reply_markup=get_broadcast_history_list_keyboard(broadcasts, page),
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data.startswith("view_broadcast:"))
async def cmd_view_broadcast(callback: CallbackQuery):
    """Обработчик просмотра деталей рассылки"""
    _, broadcast_id = callback.data.split(":", 1)
    broadcast_id = int(broadcast_id)

    # Получаем информацию о рассылке
    broadcast = get_broadcast_details(broadcast_id)

    if not broadcast:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Рассылка не найдена.",
            reply_markup=get_back_keyboard("broadcast_history"),
            parse_mode="HTML"
        )
    else:
        details_text = format_broadcast_details(broadcast)

        await callback.message.edit_text(
            details_text,
            reply_markup=get_broadcast_history_keyboard(broadcast_id),
            parse_mode="HTML"
        )

    await callback.answer()
