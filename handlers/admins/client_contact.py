import logging
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.enums import ParseMode

from filters.admin_filter import AdminFilter
from states.client_contact_state import ClientContactStates
from keyboards.admins.client_contact_keyboards import (
    get_message_type_keyboard,
    get_confirm_keyboard,
    get_back_to_menu_keyboard,
    get_cancel_keyboard, get_inline_cancel_keyboard
)
from keyboards.admins.menu_keyboard import get_admin_menu_keyboard
from database.admins.client_contact_db import (
    log_message_sent,
    get_client_info, get_client_orders
)

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(ClientContactStates.waiting_for_client_id)
async def process_client_id(message: Message, state: FSMContext):
    """Обработка введенного ID клиента"""
    if message.text == "Отмена":
        await message.answer(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        return

    try:
        client_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID. Пожалуйста, введите числовой ID клиента:"
        )
        return

    client_info = get_client_info(client_id)

    if client_info:
        info_text = (
            f"✅ <b>Клиент найден:</b>\n"
            f"ID: {client_id}\n"
        )
        if client_info.get('first_name'):
            info_text += f"Имя: {client_info['first_name']}\n"
        if client_info.get('last_name'):
            info_text += f"Фамилия: {client_info['last_name']}\n"
        if client_info.get('username'):
            info_text += f"Username: @{client_info['username']}\n"
        if client_info.get('first_login_date'):
            info_text += f"Дата регистрации: {client_info['first_login_date']}\n"

        orders = get_client_orders(client_id, limit=3)
        if orders:
            info_text += f"\n📦 Последние заказы: {len(orders)}"

        info_text += "\n\nВыберите тип сообщения:"
    else:
        info_text = (
            f"<b>⚠️ Клиент с ID <code>{client_id}</code> не найден в базе данных!</b>\n\n"
            "Вы можете продолжить отправку, если уверены в правильности ID.\n"
            "Выберите тип сообщения:"
        )

    await state.update_data(client_id=client_id, client_info=client_info)
    await message.answer(
        info_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_message_type_keyboard()
    )
    await state.set_state(ClientContactStates.waiting_for_message_type)


@router.callback_query(F.data == "client_contact", AdminFilter())
async def start_client_contact(callback: CallbackQuery, state: FSMContext):
    """Начало процесса связи с клиентом"""
    await callback.message.edit_text(
        "💬 <b>Связь с клиентом</b>\n\n"
        "Введите Telegram ID клиента, которому хотите отправить сообщение:\n\n"
        "<i>Примечание: клиент должен ранее использовать бота</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_inline_cancel_keyboard()
    )

    await callback.message.answer(
        "<b>Введите Telegram-ID из заказа:</b>",
        parse_mode='HTML')

    await state.set_state(ClientContactStates.waiting_for_client_id)
    await callback.answer()


@router.message(ClientContactStates.waiting_for_client_id)
async def process_client_id(message: Message, state: FSMContext):
    """Обработка введенного ID клиента"""
    if message.text == "Отмена":
        await message.answer(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        return

    try:
        client_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID. Пожалуйста, введите числовой ID клиента:"
        )
        return

    client_info = get_client_info(client_id)

    if client_info:
        info_text = (
            f"✅ <b>Клиент найден:</b>\n"
            f"ID: {client_id}\n"
        )
        if client_info.get('first_name'):
            info_text += f"Имя: {client_info['first_name']}\n"
        if client_info.get('username'):
            info_text += f"Username: @{client_info['username']}\n"
        if client_info.get('phone'):
            info_text += f"Телефон: {client_info['phone']}\n"

        info_text += "\nВыберите тип сообщения:"
    else:
        info_text = (
            f"<b>⚠️ Клиент с ID <code>{client_id}</code> не найден в базе данных!</b>\n\n"
            "Вы можете продолжить отправку, если уверены в правильности ID.\n"
            "Выберите тип сообщения:"
        )

    await state.update_data(client_id=client_id, client_info=client_info)
    await message.answer(
        info_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_message_type_keyboard()
    )
    await state.set_state(ClientContactStates.waiting_for_message_type)


@router.callback_query(
    ClientContactStates.waiting_for_message_type,
    F.data.in_(["msg_type_text", "msg_type_image"])
)
async def process_message_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа сообщения"""
    message_type = "text" if callback.data == "msg_type_text" else "image"
    await state.update_data(message_type=message_type)

    if message_type == "text":
        await callback.message.edit_text(
            "📝 <b>Текстовое сообщение</b>\n\n"
            "Введите текст сообщения для клиента:\n\n"
            "<i>Поддерживается HTML-форматирование</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_inline_cancel_keyboard()
        )
        await state.set_state(ClientContactStates.waiting_for_text_message)
    else:
        await callback.message.edit_text(
            "🖼️ <b>Сообщение с изображением</b>\n\n"
            "Отправьте изображение для клиента:",
            parse_mode=ParseMode.HTML
        )
        await callback.message.answer(
            "Отправьте изображение или нажмите кнопку для отмены:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ClientContactStates.waiting_for_image)

    await callback.answer()


@router.message(ClientContactStates.waiting_for_text_message, F.text)
async def process_text_message(message: Message, state: FSMContext):
    """Обработка текстового сообщения"""
    if message.text == "Отмена":
        await message.answer(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        return

    await state.update_data(message_text=message.text)
    data = await state.get_data()

    preview_text = (
        f"<b>Предпросмотр сообщения:</b>\n"
        f"Получатель: ID {data['client_id']}\n"
        f"Тип: Текстовое сообщение\n\n"
        f"<b>Текст:</b>\n{message.text}"
    )

    await message.answer(
        preview_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_confirm_keyboard(data['client_id'])
    )
    await state.set_state(ClientContactStates.confirm_sending)


@router.message(ClientContactStates.waiting_for_image, F.photo)
async def process_image(message: Message, state: FSMContext):
    """Обработка изображения"""
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)

    await message.answer(
        "✅ Изображение получено.\n\n"
        "Теперь введите текст, который будет отправлен вместе с изображением "
        "(или отправьте точку '.' для отправки без текста):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(ClientContactStates.waiting_for_image_caption)


@router.message(ClientContactStates.waiting_for_image_caption, F.text)
async def process_image_caption(message: Message, state: FSMContext):
    """Обработка подписи к изображению"""
    if message.text == "Отмена":
        await message.answer(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        return

    caption = None if message.text == "." else message.text
    await state.update_data(message_text=caption)

    data = await state.get_data()

    preview_text = (
        f"<b>Предпросмотр сообщения:</b>\n"
        f"Получатель: ID {data['client_id']}\n"
        f"Тип: Изображение\n"
    )
    if caption:
        preview_text += f"Подпись: {caption}"

    await message.answer_photo(
        photo=data['photo_file_id'],
        caption=preview_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_confirm_keyboard(data['client_id'])
    )
    await state.set_state(ClientContactStates.confirm_sending)


@router.callback_query(
    ClientContactStates.confirm_sending,
    F.data.startswith("confirm_send_")
)
async def confirm_and_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и отправка сообщения"""
    await callback.answer("Отправляю сообщение...")

    data = await state.get_data()
    client_id = data['client_id']
    admin_id = callback.from_user.id

    try:
        if data['message_type'] == 'text':
            await bot.send_message(
                chat_id=client_id,
                text=data['message_text'],
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_photo(
                chat_id=client_id,
                photo=data['photo_file_id'],
                caption=data.get('message_text'),
                parse_mode=ParseMode.HTML if data.get('message_text') else None
            )

        log_message_sent(
            admin_id=admin_id,
            client_id=client_id,
            message_text=data.get('message_text'),
            message_type=data['message_type'],
            image_file_id=data.get('photo_file_id'),
            success=True
        )

        await callback.message.answer(
            "✅ <b>Сообщение успешно отправлено!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_menu_keyboard()
        )

    except TelegramForbiddenError:
        error_msg = "Бот заблокирован пользователем"
        log_message_sent(
            admin_id=admin_id,
            client_id=client_id,
            message_text=data.get('message_text'),
            message_type=data['message_type'],
            image_file_id=data.get('photo_file_id'),
            success=False,
            error_message=error_msg
        )

        await callback.message.answer(
            f"❌ <b>Ошибка:</b> {error_msg}\n"
            "Пользователь заблокировал бота или не начинал с ним диалог.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_menu_keyboard()
        )

    except TelegramBadRequest as e:
        error_msg = str(e)
        log_message_sent(
            admin_id=admin_id,
            client_id=client_id,
            message_text=data.get('message_text'),
            message_type=data['message_type'],
            image_file_id=data.get('photo_file_id'),
            success=False,
            error_message=error_msg
        )

        await callback.message.answer(
            f"❌ <b>Ошибка отправки:</b> {error_msg}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        await callback.message.answer(
            "❌ Произошла непредвиденная ошибка при отправке сообщения.\n"
            "🛠 Убедительная просьба связаться с техническим персоналом.",
            reply_markup=get_back_to_menu_keyboard()
        )

    await state.clear()


@router.callback_query(F.data == "edit_message")
async def edit_message(callback: CallbackQuery, state: FSMContext):
    """Редактирование сообщения"""
    data = await state.get_data()

    if data['message_type'] == 'text':
        await callback.message.answer(
            "📝 Введите новый текст сообщения:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ClientContactStates.waiting_for_text_message)
    else:
        await callback.message.answer(
            "🖼️ Отправьте новое изображение:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ClientContactStates.waiting_for_image)

    await callback.answer()


@router.callback_query(F.data == "client_contact_cancel", StateFilter("*"))
async def cancel_client_contact(callback: CallbackQuery, state: FSMContext):
    """Отмена операции связи с клиентом"""
    try:
        await callback.message.edit_text(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )
    except TelegramBadRequest:
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )

    await callback.message.answer(
        "Возврат в главное меню",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()
    await callback.answer()


@router.message(ClientContactStates.waiting_for_image, ~F.photo)
async def process_wrong_type_for_image(message: Message, state: FSMContext):
    """Обработка неверного типа сообщения при ожидании изображения"""
    if message.text == "Отмена":
        await message.answer(
            "Операция отменена",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        return

    await message.answer(
        "❌ Пожалуйста, отправьте изображение или нажмите 'Отмена'",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню администратора"""
    await callback.message.edit_text(
        "Главное меню администратора:",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()
    await callback.answer()
