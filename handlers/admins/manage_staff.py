import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.admins.staff_db import (
    get_staff_roles, get_staff_by_role, get_all_active_staff,
    get_staff_by_id, add_staff_member, update_staff_role,
    update_staff_access_level, toggle_staff_status, delete_staff_member,
    get_staff_by_telegram_id, get_all_available_roles
)
from filters.admin_filter import AdminFilter
from keyboards.admins.staff_keyboards import (
    get_staff_management_keyboard, get_staff_roles_keyboard,
    get_staff_list_keyboard, get_staff_detail_keyboard,
    get_role_selection_keyboard, get_confirmation_keyboard,
    get_skip_keyboard, get_staff_statuses_keyboard, get_cancel_keyboard, get_cancel_keyboard_create_status,
    get_description_step_keyboard
)
from states.staff_state import StaffAddStates, StaffEditStates, StaffStatusCreateState
from database.admins.staff_db import (
    get_all_staff_statuses, add_new_staff_status, get_staff_status_details
)

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

# Обработчик для входа в меню управления персоналом
@router.callback_query(F.data == "manage_staff")
async def staff_management_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🧑‍💼 Меню управления персоналом",
        reply_markup=get_staff_management_keyboard()
    )


# Обработчик для просмотра сотрудников (фильтрация по ролям)
@router.callback_query(F.data == "staff_view")
async def staff_view_roles(callback: CallbackQuery):
    await callback.answer()

    # Получаем список всех доступных ролей (включая недавно созданные)
    roles = get_all_available_roles()

    await callback.message.edit_text(
        "🔍 Выберите роль сотрудников для просмотра:",
        reply_markup=get_staff_roles_keyboard(roles)
    )


# Обработчик для просмотра сотрудников по выбранной роли
@router.callback_query(F.data.startswith("staff_role_"))
async def staff_list_by_role(callback: CallbackQuery):
    await callback.answer()

    # Извлекаем роль из callback_data
    role = callback.data.split("_")[2]

    # Получаем список сотрудников с выбранной ролью
    staff_list = get_staff_by_role(role)

    if not staff_list:
        await callback.message.edit_text(
            f"❔ Сотрудники с ролью '{role}' <b>не найдены</b>.",
            reply_markup=get_staff_roles_keyboard(get_staff_roles()),
            parse_mode='HTML'
        )
        return

    await callback.message.edit_text(
        f"Список сотрудников с ролью '{role}':",
        reply_markup=get_staff_list_keyboard(staff_list)
    )


# Обработчик для просмотра всех сотрудников
@router.callback_query(F.data == "staff_all")
async def staff_list_all(callback: CallbackQuery):
    await callback.answer()

    # Получаем список всех активных сотрудников
    staff_list = get_all_active_staff()

    if not staff_list:
        await callback.message.edit_text(
            "Активные сотрудники не найдены.",
            reply_markup=get_staff_roles_keyboard(get_staff_roles())
        )
        return

    await callback.message.edit_text(
        "Список всех <b>активных</b> сотрудников:",
        reply_markup=get_staff_list_keyboard(staff_list),
        parse_mode='HTML'
    )


# Обработчик для просмотра детальной информации о сотруднике
@router.callback_query(F.data.startswith("staff_id_"))
async def staff_detail(callback: CallbackQuery):
    await callback.answer()

    # Извлекаем ID сотрудника из callback_data
    staff_id = int(callback.data.split("_")[2])

    # Получаем информацию о сотруднике
    staff = get_staff_by_id(staff_id)

    if not staff:
        await callback.message.edit_text(
            "Сотрудник не найден. Возможно, он был удален.",
            reply_markup=get_staff_management_keyboard()
        )
        return

    # Формируем сообщение с информацией о сотруднике
    staff_info = (
        f"👤 <b>Профиль сотрудника</b>\n\n"
        f"ID: {staff['id']}\n"
        f"Telegram ID: {staff['telegram_id']}\n"
        f"Username: {staff['username'] or 'Не указан'}\n"
        f"Имя: {staff['first_name']}\n"
        f"Фамилия: {staff['last_name'] or 'Не указана'}\n"
        f"Телефон: {staff['phone'] or 'Не указан'}\n"
        f"Роль: {staff['role']}\n"
        f"Уровень доступа: {staff['access_level']}\n"
        f"Статус: {'Активен' if staff['is_active'] else 'Заблокирован'}\n"
        f"Дата регистрации: {staff['created_at']}\n"
        f"Последний вход: {staff['last_login'] or 'Нет данных'}"
    )

    await callback.message.edit_text(
        staff_info,
        reply_markup=get_staff_detail_keyboard(staff_id, staff['is_active']),
        parse_mode="HTML"
    )


# Обработчик для возврата в главное меню управления персоналом
@router.callback_query(F.data == "staff_management")
async def return_to_staff_management(callback: CallbackQuery):
    await callback.answer()
    await staff_management_menu(callback)


# Обработчик для возврата в меню администратора
@router.callback_query(F.data == "admin_menu")
async def return_to_admin_menu(callback: CallbackQuery):
    await callback.answer()
    # Здесь должен быть вызов обработчика меню администратора из другого файла
    # Реализация зависит от существующего кода
    await callback.message.edit_text(
        "Возвращаемся в главное меню администратора...",
        reply_markup=None
    )


# Обработчики изменения роли сотрудника
@router.callback_query(F.data.startswith("staff_change_role_"))
async def change_staff_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Извлекаем ID сотрудника из callback_data
    staff_id = int(callback.data.split("_")[3])

    # Сохраняем ID сотрудника в памяти состояния
    await state.update_data(staff_id=staff_id)

    # Получаем список всех доступных ролей, включая недавно созданные
    roles = get_all_available_roles()

    await callback.message.edit_text(
        "Выберите новую роль для сотрудника:",
        reply_markup=get_role_selection_keyboard(roles, "staff_set_role")
    )

    # Устанавливаем состояние для ожидания выбора роли
    await state.set_state(StaffEditStates.new_role)


@router.callback_query(StaffEditStates.new_role, F.data.startswith("staff_set_role_"))
async def set_staff_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Извлекаем новую роль из callback_data
    new_role = callback.data.split("_")[3]

    # Получаем ID сотрудника из памяти состояния
    data = await state.get_data()
    staff_id = data.get("staff_id")

    # Обновляем роль сотрудника
    success = update_staff_role(staff_id, new_role)

    if success:
        # Получаем обновленную информацию о сотруднике
        staff = get_staff_by_id(staff_id)

        # Формируем сообщение с обновленной информацией
        staff_info = (
            f"<b>Профиль сотрудника (роль обновлена)</b>\n\n"
            f"ID: {staff['id']}\n"
            f"Telegram ID: {staff['telegram_id']}\n"
            f"Username: {staff['username'] or 'Не указан'}\n"
            f"Имя: {staff['first_name']}\n"
            f"Фамилия: {staff['last_name'] or 'Не указана'}\n"
            f"Телефон: {staff['phone'] or 'Не указан'}\n"
            f"Роль: {staff['role']}\n"
            f"Уровень доступа: {staff['access_level']}\n"
            f"Статус: {'Активен' if staff['is_active'] else 'Заблокирован'}\n"
            f"Дата регистрации: {staff['created_at']}\n"
            f"Последний вход: {staff['last_login'] or 'Нет данных'}"
        )

        await callback.message.edit_text(
            staff_info,
            reply_markup=get_staff_detail_keyboard(staff_id, staff['is_active']),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "Произошла ошибка при обновлении роли сотрудника.",
            reply_markup=get_staff_detail_keyboard(staff_id, True)
        )

    # Сбрасываем состояние
    await state.clear()


# Обработчики изменения уровня доступа
@router.callback_query(F.data.startswith("staff_change_access_"))
async def change_staff_access(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Извлекаем ID сотрудника из callback_data
    staff_id = int(callback.data.split("_")[3])

    # Сохраняем ID сотрудника в памяти состояния
    await state.update_data(staff_id=staff_id)

    await callback.message.edit_text(
        "Введите новый уровень доступа для сотрудника (число от 1 до 5):",
        reply_markup=None
    )

    # Устанавливаем состояние для ожидания ввода уровня доступа
    await state.set_state(StaffEditStates.new_access_level)


@router.message(StaffEditStates.new_access_level)
async def set_staff_access_level(message: Message, state: FSMContext):
    # Проверяем, что введено корректное число
    try:
        new_level = int(message.text)
        if not 1 <= new_level <= 5:
            await message.answer(
                "Уровень доступа должен быть числом от 1 до 5. Попробуйте еще раз:",
                reply_markup=None
            )
            return
    except ValueError:
        await message.answer(
            "Введите корректное число от 1 до 5:",
            reply_markup=None
        )
        return

    # Получаем ID сотрудника из памяти состояния
    data = await state.get_data()
    staff_id = data.get("staff_id")

    # Обновляем уровень доступа сотрудника
    success = update_staff_access_level(staff_id, new_level)

    if success:
        # Получаем обновленную информацию о сотруднике
        staff = get_staff_by_id(staff_id)

        # Формируем сообщение с обновленной информацией
        staff_info = (
            f"<b>Профиль сотрудника (уровень доступа обновлен)</b>\n\n"
            f"ID: {staff['id']}\n"
            f"Telegram ID: {staff['telegram_id']}\n"
            f"Username: {staff['username'] or 'Не указан'}\n"
            f"Имя: {staff['first_name']}\n"
            f"Фамилия: {staff['last_name'] or 'Не указана'}\n"
            f"Телефон: {staff['phone'] or 'Не указан'}\n"
            f"Роль: {staff['role']}\n"
            f"Уровень доступа: {staff['access_level']}\n"
            f"Статус: {'Активен' if staff['is_active'] else 'Заблокирован'}\n"
            f"Дата регистрации: {staff['created_at']}\n"
            f"Последний вход: {staff['last_login'] or 'Нет данных'}"
        )

        await message.answer(
            staff_info,
            reply_markup=get_staff_detail_keyboard(staff_id, staff['is_active']),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Произошла ошибка при обновлении уровня доступа сотрудника.",
            reply_markup=get_staff_detail_keyboard(staff_id, True)
        )

    # Сбрасываем состояние
    await state.clear()


# Обработчик для изменения статуса активности сотрудника
@router.callback_query(F.data.startswith("staff_toggle_status_"))
async def toggle_staff_active_status(callback: CallbackQuery):
    await callback.answer()

    # Извлекаем ID сотрудника из callback_data
    staff_id = int(callback.data.split("_")[3])

    # Изменяем статус активности сотрудника
    success = toggle_staff_status(staff_id)

    if success:
        # Получаем обновленную информацию о сотруднике
        staff = get_staff_by_id(staff_id)

        status_text = "заблокирован" if not staff['is_active'] else "активирован"

        # Формируем сообщение с обновленной информацией
        staff_info = (
            f"<b>Профиль сотрудника (статус {status_text})</b>\n\n"
            f"ID: {staff['id']}\n"
            f"Telegram ID: {staff['telegram_id']}\n"
            f"Username: {staff['username'] or 'Не указан'}\n"
            f"Имя: {staff['first_name']}\n"
            f"Фамилия: {staff['last_name'] or 'Не указана'}\n"
            f"Телефон: {staff['phone'] or 'Не указан'}\n"
            f"Роль: {staff['role']}\n"
            f"Уровень доступа: {staff['access_level']}\n"
            f"Статус: {'Активен' if staff['is_active'] else 'Заблокирован'}\n"
            f"Дата регистрации: {staff['created_at']}\n"
            f"Последний вход: {staff['last_login'] or 'Нет данных'}"
        )

        await callback.message.edit_text(
            staff_info,
            reply_markup=get_staff_detail_keyboard(staff_id, staff['is_active']),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "Произошла ошибка при изменении статуса сотрудника.",
            reply_markup=get_staff_detail_keyboard(staff_id, True)
        )


# Обработчики удаления сотрудника
@router.callback_query(F.data.startswith("staff_delete_"))
async def confirm_delete_staff(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Извлекаем ID сотрудника из callback_data
    staff_id = int(callback.data.split("_")[2])

    # Сохраняем ID сотрудника в памяти состояния
    await state.update_data(staff_id=staff_id)

    # Получаем информацию о сотруднике
    staff = get_staff_by_id(staff_id)

    # Запрашиваем подтверждение удаления
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить сотрудника?\n\n"
        f"Имя: {staff['first_name']} {staff['last_name'] or ''}\n"
        f"Роль: {staff['role']}\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=get_confirmation_keyboard("delete", staff_id)
    )

    # Устанавливаем состояние для ожидания подтверждения
    await state.set_state(StaffEditStates.confirm_delete)


@router.callback_query(StaffEditStates.confirm_delete, F.data.startswith("staff_confirm_delete_"))
async def delete_staff_confirmed(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Извлекаем ID сотрудника из callback_data
    staff_id = int(callback.data.split("_")[3])

    # Удаляем сотрудника
    success = delete_staff_member(staff_id)

    if success:
        await callback.message.edit_text(
            "✅ Сотрудник успешно удален.",
            reply_markup=get_staff_management_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении сотрудника.",
            reply_markup=get_staff_management_keyboard()
        )

    # Сбрасываем состояние
    await state.clear()


# Обработчики добавления нового сотрудника
@router.callback_query(F.data == "staff_add")
async def start_add_staff(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.edit_text(
        "Введите Telegram ID нового сотрудника.\n"
        "ID должен быть числом, например: 123456789",
        reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
    )

    # Устанавливаем состояние для ожидания ввода Telegram ID
    await state.set_state(StaffAddStates.telegram_id)


@router.message(StaffAddStates.telegram_id)
async def process_telegram_id(message: Message, state: FSMContext):
    # Проверяем, что введен корректный ID
    try:
        telegram_id = int(message.text)
    except ValueError:
        await message.answer(
            "Введите корректный Telegram ID (только цифры):",
            reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
        )
        return

        # Проверяем, не существует ли уже сотрудник с таким ID
    existing_staff = get_staff_by_telegram_id(telegram_id)
    if existing_staff:
        await message.answer(
            f"Сотрудник с таким Telegram ID уже существует:\n"
            f"Имя: {existing_staff['first_name']} {existing_staff['last_name'] or ''}\n"
            f"Роль: {existing_staff['role']}\n\n"
            f"Введите другой Telegram ID:",
            reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
        )
        return

        # Сохраняем Telegram ID в памяти состояния
    await state.update_data(telegram_id=telegram_id)

    # Запрашиваем имя сотрудника
    await message.answer(
        "Введите имя сотрудника:",
        reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
    )

    # Переходим к следующему состоянию - ввод имени
    await state.set_state(StaffAddStates.first_name)


@router.message(StaffAddStates.first_name)
async def process_first_name(message: Message, state: FSMContext):
    # Сохраняем имя в памяти состояния
    await state.update_data(first_name=message.text)

    # Запрашиваем фамилию
    await message.answer(
        "Введите фамилию сотрудника (или отправьте '-' чтобы пропустить):",
        reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
    )

    # Переходим к следующему состоянию - ввод фамилии
    await state.set_state(StaffAddStates.last_name)


@router.message(StaffAddStates.last_name)
async def process_last_name(message: Message, state: FSMContext):
    # Сохраняем фамилию в памяти состояния, если не был отправлен символ пропуска
    last_name = None if message.text == '-' else message.text
    await state.update_data(last_name=last_name)

    # Запрашиваем номер телефона
    await message.answer(
        "Введите номер телефона сотрудника:",
        reply_markup=get_skip_keyboard()
    )

    # Переходим к следующему состоянию - ввод телефона
    await state.set_state(StaffAddStates.phone)


@router.message(StaffAddStates.phone)
async def process_phone(message: Message, state: FSMContext):
    # Сохраняем номер телефона в памяти состояния
    await state.update_data(phone=message.text)

    # Запрашиваем выбор роли - используем все доступные роли, включая недавно созданные
    roles = get_all_available_roles()

    await message.answer(
        "Выберите роль для нового сотрудника:",
        reply_markup=get_role_selection_keyboard(roles)
    )

    # Переходим к следующему состоянию - выбор роли
    await state.set_state(StaffAddStates.role)


@router.callback_query(StaffAddStates.phone, F.data == "staff_skip")
async def skip_phone(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Сохраняем None вместо номера телефона
    await state.update_data(phone=None)

    # Запрашиваем выбор роли - используем все доступные роли, включая недавно созданные
    roles = get_all_available_roles()

    await callback.message.edit_text(
        "Выберите роль для нового сотрудника:",
        reply_markup=get_role_selection_keyboard(roles)
    )

    # Переходим к следующему состоянию - выбор роли
    await state.set_state(StaffAddStates.role)


@router.callback_query(StaffAddStates.role, F.data.startswith("staff_select_role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Извлекаем выбранную роль из callback_data
    role = callback.data.split("_")[3]

    # Сохраняем роль в памяти состояния
    await state.update_data(role=role)

    # Запрашиваем уровень доступа
    await callback.message.edit_text(
        "Введите уровень доступа для сотрудника (число от 1 до 5):",
        reply_markup=None
    )

    # Переходим к следующему состоянию - ввод уровня доступа
    await state.set_state(StaffAddStates.access_level)


@router.message(StaffAddStates.access_level)
async def process_access_level(message: Message, state: FSMContext):
    # Проверяем, что введено корректное число
    try:
        access_level = int(message.text)
        if not 1 <= access_level <= 5:
            await message.answer(
                "Уровень доступа должен быть числом от 1 до 5. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
            )
            return
    except ValueError:
        await message.answer(
            "Введите корректное число от 1 до 5:",
            reply_markup=get_cancel_keyboard()  # Добавляем клавиатуру отмены
        )
        return

    # Сохраняем уровень доступа в памяти состояния
    await state.update_data(access_level=access_level)

    # Получаем все данные из памяти состояния
    data = await state.get_data()

    # Формируем сообщение с данными нового сотрудника для подтверждения
    confirm_text = (
        f"Проверьте введенные данные:\n\n"
        f"Telegram ID: {data['telegram_id']}\n"
        f"Имя: {data['first_name']}\n"
        f"Фамилия: {data.get('last_name') or 'Не указана'}\n"
        f"Телефон: {data.get('phone') or 'Не указан'}\n"
        f"Роль: {data['role']}\n"
        f"Уровень доступа: {data['access_level']}\n\n"
        f"ℹ️ Подтвердите добавление нового сотрудника:"
    )

    await message.answer(
        confirm_text,
        reply_markup=get_confirmation_keyboard("add")
    )

    # Переходим к следующему состоянию - подтверждение добавления
    await state.set_state(StaffAddStates.confirm)


@router.callback_query(StaffAddStates.confirm, F.data == "staff_confirm_add")
async def confirm_add_staff(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Получаем все данные из памяти состояния
    data = await state.get_data()

    # Добавляем нового сотрудника в базу данных
    success = add_staff_member(
        telegram_id=data['telegram_id'],
        username=None,  # Будет обновлено при первом входе сотрудника
        first_name=data['first_name'],
        last_name=data.get('last_name'),
        phone=data.get('phone'),
        role=data['role'],
        access_level=data['access_level']
    )

    if success:
        await callback.message.edit_text(
            "✅ Новый сотрудник успешно добавлен!",
            reply_markup=get_staff_management_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при добавлении сотрудника. Возможно, сотрудник с таким Telegram ID уже существует.",
            reply_markup=get_staff_management_keyboard()
        )

    # Сбрасываем состояние
    await state.clear()


# Общий обработчик отмены действий
@router.callback_query(F.data == "staff_cancel")
async def cancel_staff_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Получаем текущее состояние
    current_state = await state.get_state()

    if current_state:
        # Если есть активное состояние, очищаем его
        await state.clear()

    await callback.message.edit_text(
        "Действие отменено.",
        reply_markup=get_staff_management_keyboard()
    )


# Обработчик для просмотра списка статусов
@router.callback_query(F.data == "staff_view_statuses")
async def view_staff_statuses(callback: CallbackQuery):
    await callback.answer()

    # Получаем список всех статусов
    statuses = get_all_staff_statuses()

    if not statuses:
        await callback.message.edit_text(
            "В системе пока нет созданных статусов (ролей) сотрудников.",
            reply_markup=get_staff_management_keyboard()
        )
        return

    await callback.message.edit_text(
        "📋 Доступные статусы (роли) сотрудников:",
        reply_markup=get_staff_statuses_keyboard(statuses)
    )


# Обработчик для просмотра деталей статуса
@router.callback_query(F.data.startswith("staff_status_view_"))
async def view_staff_status_details(callback: CallbackQuery):
    await callback.answer()

    # Извлекаем название статуса из callback_data
    status_name = callback.data.split("_")[3]

    # Получаем детали статуса
    status_details = get_staff_status_details(status_name)

    if not status_details:
        await callback.message.edit_text(
            f"Статус '{status_name}' не найден.",
            reply_markup=get_staff_management_keyboard()
        )
        return

    # Формируем сообщение с деталями статуса
    message_text = (
        f"📊 <b>Информация о статусе (роли)</b>\n\n"
        f"📝 Название: {status_details['role_name']}\n"
    )

    if 'description' in status_details and status_details['description']:
        message_text += f"📄 Описание: {status_details['description']}\n"

    if 'created_at' in status_details and status_details['created_at']:
        message_text += f"📅 Создан: {status_details['created_at']}\n"

    if 'count' in status_details:
        message_text += f"👥 Количество сотрудников с этой ролью: {status_details['count']}\n"

    # Получаем список всех статусов
    statuses = get_all_staff_statuses()

    await callback.message.edit_text(
        message_text,
        reply_markup=get_staff_statuses_keyboard(statuses),
        parse_mode="HTML"
    )


# Обработчик для начала создания нового статуса
@router.callback_query(F.data == "staff_create_status")
async def start_create_status(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.edit_text(
        "🆕 Создание нового статуса (роли) сотрудника\n\n"
        "Введите название нового статуса:",
        reply_markup=get_cancel_keyboard_create_status()  # Добавляем кнопку отмены
    )

    # Устанавливаем состояние для ожидания ввода названия статуса
    await state.set_state(StaffStatusCreateState.status_name)


# Обработчик для получения названия статуса
@router.message(StaffStatusCreateState.status_name)
async def process_status_name(message: Message, state: FSMContext):
    # Проверяем название статуса
    status_name = message.text.strip()

    if not status_name:
        await message.answer(
            "Название статуса не может быть пустым. Введите название:",
            reply_markup=get_cancel_keyboard()
        )
        return

        # Проверяем, не существует ли уже такой статус
    existing_statuses = get_all_staff_statuses()
    if status_name in existing_statuses:
        await message.answer(
            f"Статус с названием '{status_name}' уже существует. Введите другое название:",
            reply_markup=get_cancel_keyboard()
        )
        return

        # Сохраняем название в памяти состояния
    await state.update_data(status_name=status_name)

    # Запрашиваем описание статуса с кнопкой пропуска
    await message.answer(
        "Введите описание статуса (или нажмите кнопку «Пропустить»):",
        reply_markup=get_description_step_keyboard()  # Используем клавиатуру с кнопкой пропуска
    )

    # Переходим к следующему состоянию - ввод описания
    await state.set_state(StaffStatusCreateState.status_description)


# Добавляем обработчик для отмены действия
@router.callback_query(F.data == "staff_cancel")
async def cancel_staff_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Очищаем состояние
    await state.clear()

    # Возвращаемся в меню управления персоналом
    await callback.message.edit_text(
        "🔄 Действие отменено.\n\n🧑‍💼 Меню управления персоналом",
        reply_markup=get_staff_management_keyboard()
    )


# Обработчик для получения описания статуса
@router.message(StaffStatusCreateState.status_description)
async def process_status_description(message: Message, state: FSMContext):
    # Сохраняем описание в памяти состояния, если не был отправлен символ пропуска
    description = None if message.text == '-' else message.text
    await state.update_data(status_description=description)

    # Получаем все данные из памяти состояния
    data = await state.get_data()

    # Формируем сообщение с данными нового статуса для подтверждения
    confirm_text = (
        f"Проверьте данные нового статуса:\n\n"
        f"📝 Название: {data['status_name']}\n"
    )

    if data.get('status_description'):
        confirm_text += f"📄 Описание: {data['status_description']}\n\n"
    else:
        confirm_text += "📄 Описание: Не указано\n\n"

    confirm_text += "Подтвердите создание нового статуса:"

    await message.answer(
        confirm_text,
        reply_markup=get_confirmation_keyboard("status")
    )

    # Переходим к следующему состоянию - подтверждение создания
    await state.set_state(StaffStatusCreateState.confirm)


# Обработчик для пропуска описания статуса
@router.callback_query(StaffStatusCreateState.status_description, F.data == "staff_skip_description")
async def skip_status_description(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Сохраняем None вместо описания
    await state.update_data(status_description=None)

    # Получаем все данные из памяти состояния
    data = await state.get_data()

    # Формируем сообщение с данными нового статуса для подтверждения
    confirm_text = (
        f"Проверьте данные нового статуса:\n\n"
        f"📝 Название: {data['status_name']}\n"
        f"📄 Описание: Не указано\n\n"
        f"Подтвердите создание нового статуса:"
    )

    await callback.message.edit_text(
        confirm_text,
        reply_markup=get_confirmation_keyboard("status")
    )

    # Переходим к следующему состоянию - подтверждение создания
    await state.set_state(StaffStatusCreateState.confirm)


# Обработчик для подтверждения создания статуса
@router.callback_query(StaffStatusCreateState.confirm, F.data == "staff_confirm_status")
async def confirm_create_status(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Получаем все данные из памяти состояния
    data = await state.get_data()

    # Добавляем новый статус в базу данных
    success, message = add_new_staff_status(
        status_name=data['status_name'],
        status_description=data.get('status_description')
    )

    if success:
        await callback.message.edit_text(
            f"✅ Новый статус '{data['status_name']}' успешно создан!\n\n"
            f"Теперь вы можете:\n"
            f"• Просматривать сотрудников с этой ролью\n"
            f"• Назначать эту роль при добавлении новых сотрудников\n"
            f"• Изменять роли существующих сотрудников на '{data['status_name']}'",
            reply_markup=get_staff_management_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"❌ Произошла ошибка при создании статуса: {message}",
            reply_markup=get_staff_management_keyboard()
        )

    # Сбрасываем состояние
    await state.clear()


@router.callback_query(F.data == "staff_management")
async def return_to_staff_management(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🧑‍💼 Меню управления персоналом",
        reply_markup=get_staff_management_keyboard()
    )
