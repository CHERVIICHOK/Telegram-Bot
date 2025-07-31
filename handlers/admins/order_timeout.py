from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

from keyboards.admins.order_timeout_keyboard import (
    get_timeout_main_menu_keyboard,
    get_timeout_settings_keyboard,
    get_interval_settings_keyboard,
    get_text_settings_keyboard,
    get_confirm_timeout_keyboard,
    get_confirm_interval_keyboard,
    get_confirm_text_keyboard
)
from database.admins.settings_db import (
    get_order_processing_timeout,
    update_order_processing_timeout,
    get_notification_interval,
    update_notification_interval,
    get_notification_text,
    update_notification_text,
    DEFAULT_NOTIFICATION_TEXT
)
from filters.admin_filter import AdminFilter
from states.order_timeout_state import TimeoutSettingsStates

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())



async def _show_timeout_main_menu(message_or_callback):
    """Показывает главное меню настроек таймаута"""
    current_timeout = get_order_processing_timeout()
    current_interval = get_notification_interval()

    text = (
        "⏱️ <b>Настройки уведомлений для необработанных заказах</b>\n\n"
        f"📍 Время первого уведомления: <b>{current_timeout} мин.</b>\n"
        f"🔄 Интервал повторных уведомлений: <b>{current_interval} мин.</b>\n\n"
        "Выберите, что хотите настроить:"
    )
    keyboard = get_timeout_main_menu_keyboard()

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message_or_callback.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


# Главное меню настроек таймаута
@router.callback_query(F.data == "timeout_settings")
async def show_timeout_main_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает главное меню настроек таймаута"""
    await state.clear()
    await _show_timeout_main_menu(callback)
    await callback.answer()


# Настройка времени первого уведомления
@router.callback_query(F.data == "timeout_first_notification")
async def show_timeout_settings(callback: CallbackQuery):
    """Показывает настройки времени первого уведомления"""
    current_timeout = get_order_processing_timeout()
    keyboard = get_timeout_settings_keyboard(current_timeout)

    await callback.message.edit_text(
        "⏱️ <b>Время первого уведомления</b>\n\n"
        "Установите время, через которое курьеры получат первое "
        "уведомление о необработанном заказе.\n\n"
        "Выберите время из предложенных вариантов или введите свое:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_timeout:"))
async def process_set_timeout(callback: CallbackQuery):
    """Обрабатывает установку времени таймаута"""
    minutes = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        f"Установить время первого уведомления: <b>{minutes} мин.</b>?",
        reply_markup=get_confirm_timeout_keyboard(minutes),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "custom_timeout")
async def process_custom_timeout(callback: CallbackQuery, state: FSMContext):
    """Запрашивает ввод произвольного времени"""
    await state.set_state(TimeoutSettingsStates.entering_custom_time)

    await callback.message.edit_text(
        "Введите время первого уведомления в минутах (от 1 до 1440):\n\n"
        "Например: 25"
    )
    await callback.answer()


@router.message(TimeoutSettingsStates.entering_custom_time)
async def process_custom_time_input(message: Message, state: FSMContext):
    """Обрабатывает ввод произвольного времени"""
    try:
        minutes = int(message.text.strip())

        if minutes < 1 or minutes > 1440:
            await message.answer(
                "❌ Время должно быть от 1 до 1440 минут (24 часа).\n"
                "Попробуйте еще раз:"
            )
            return

        await state.clear()

        await message.answer(
            f"Установить время первого уведомления: <b>{minutes} мин.</b>?",
            reply_markup=get_confirm_timeout_keyboard(minutes),
            parse_mode="HTML"
        )

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число.\n"
            "Например: 25"
        )


@router.callback_query(F.data.startswith("confirm_timeout:"))
async def process_confirm_timeout(callback: CallbackQuery):
    """Подтверждает изменение таймаута"""
    minutes = int(callback.data.split(":")[1])

    success = update_order_processing_timeout(minutes)

    if success:
        await callback.answer("✅ Время первого уведомления обновлено", show_alert=True)
        await _show_timeout_main_menu(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении настроек", show_alert=True)


# Настройка интервала повторных уведомлений
@router.callback_query(F.data == "timeout_interval")
async def show_interval_settings(callback: CallbackQuery):
    """Показывает настройки интервала повторных уведомлений"""
    current_interval = get_notification_interval()
    keyboard = get_interval_settings_keyboard(current_interval)

    await callback.message.edit_text(
        "🔄 <b>Интервал повторных уведомлений</b>\n\n"
        "Установите интервал, с которым будут отправляться "
        "повторные уведомления о необработанном заказе.\n\n"
        "Выберите интервал из предложенных вариантов или введите свой:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_interval:"))
async def process_set_interval(callback: CallbackQuery):
    """Обрабатывает установку интервала"""
    minutes = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        f"Установить интервал повторных уведомлений: <b>{minutes} мин.</b>?",
        reply_markup=get_confirm_interval_keyboard(minutes),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "custom_interval")
async def process_custom_interval(callback: CallbackQuery, state: FSMContext):
    """Запрашивает ввод произвольного интервала"""
    await state.set_state(TimeoutSettingsStates.entering_custom_interval)

    await callback.message.edit_text(
        "Введите интервал в минутах (от 1 до 1440):\n\n"
        "Например: 15"
    )
    await callback.answer()


@router.message(TimeoutSettingsStates.entering_custom_interval)
async def process_custom_interval_input(message: Message, state: FSMContext):
    """Обрабатывает ввод произвольного интервала"""
    try:
        minutes = int(message.text.strip())

        if minutes < 1 or minutes > 1440:
            await message.answer(
                "❌ Интервал должен быть от 1 до 1440 минут (24 часа).\n"
                "Попробуйте еще раз:"
            )
            return

        await state.clear()

        await message.answer(
            f"Установить интервал повторных уведомлений: <b>{minutes} мин.</b>?",
            reply_markup=get_confirm_interval_keyboard(minutes),
            parse_mode="HTML"
        )

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число.\n"
            "Например: 15"
        )


@router.callback_query(F.data.startswith("confirm_interval:"))
async def process_confirm_interval(callback: CallbackQuery):
    """Подтверждает изменение интервала"""
    minutes = int(callback.data.split(":")[1])

    success = update_notification_interval(minutes)

    if success:
        await callback.answer("✅ Интервал уведомлений обновлен", show_alert=True)
        await _show_timeout_main_menu(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении настроек", show_alert=True)


# Настройка текста уведомления
@router.callback_query(F.data == "timeout_text")
async def show_text_settings(callback: CallbackQuery):
    """Показывает настройки текста уведомления"""
    current_text = get_notification_text()

    await callback.message.edit_text(
        "📝 <b>Текст уведомления</b>\n\n"
        "<b>Текущий текст:</b>\n"
        f"<code>{current_text}</code>\n\n"
        "<b>Доступные переменные:</b>\n"
        "• <code>{order_id}</code> - номер заказа\n"
        "• <code>{elapsed_time}</code> - время с момента создания заказа\n"
        "• <code>{notification_count}</code> - номер уведомления\n\n"
        "Выберите действие:",
        reply_markup=get_text_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "edit_notification_text")
async def process_edit_text(callback: CallbackQuery, state: FSMContext):
    """Запрашивает ввод нового текста уведомления"""
    await state.set_state(TimeoutSettingsStates.entering_notification_text)

    await callback.message.edit_text(
        "📝 <b>Введите новый текст уведомления</b>\n\n"
        "<b>Доступные переменные:</b>\n"
        "• <code>{order_id}</code> - номер заказа\n"
        "• <code>{elapsed_time}</code> - время с момента создания заказа\n"
        "• <code>{notification_count}</code> - номер уведомления\n\n"
        "<b>Пример:</b>\n"
        "<code>⚠️ Заказ #{order_id} ждет обработки уже {elapsed_time} мин.!</code>\n\n"
        "Отправьте новый текст:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(TimeoutSettingsStates.entering_notification_text)
async def process_text_input(message: Message, state: FSMContext):
    """Обрабатывает ввод текста уведомления"""
    new_text = message.text.strip()

    if len(new_text) < 10:
        await message.answer(
            "❌ Текст слишком короткий. Минимум 10 символов.\n"
            "Попробуйте еще раз:"
        )
        return

    if len(new_text) > 4000:
        await message.answer(
            "❌ Текст слишком длинный. Максимум 4000 символов.\n"
            "Попробуйте сократить текст:"
        )
        return

    await state.update_data(new_notification_text=new_text)

    try:
        preview_text = new_text.format(
            order_id=12345,
            elapsed_time=30,
            notification_count=2
        )
    except KeyError as e:
        await message.answer(
            f"❌ Ошибка в тексте: неизвестная переменная {e}\n"
            f"Используйте только доступные переменные:\n"
            f"• {{order_id}}\n"
            f"• {{elapsed_time}}\n"
            f"• {{notification_count}}"
        )
        return

    await state.clear()
    await state.update_data(new_notification_text=new_text)

    await message.answer(
        f"<b>Предпросмотр уведомления:</b>\n\n"
        f"{preview_text}\n\n"
        f"Сохранить этот текст?",
        reply_markup=get_confirm_text_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_notification_text")
async def process_confirm_text(callback: CallbackQuery, state: FSMContext):
    """Подтверждает изменение текста"""
    data = await state.get_data()
    new_text = data.get('new_notification_text')

    if not new_text:
        await callback.answer("❌ Текст не найден", show_alert=True)
        return

    success = update_notification_text(new_text)

    if success:
        await state.clear()
        await callback.answer("✅ Текст уведомления обновлен", show_alert=True)
        await _show_timeout_main_menu(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении текста", show_alert=True)


@router.callback_query(F.data == "reset_notification_text")
async def process_reset_text(callback: CallbackQuery):
    """Сбрасывает текст на стандартный"""
    success = update_notification_text(DEFAULT_NOTIFICATION_TEXT)

    if success:
        await callback.answer("✅ Текст сброшен на стандартный", show_alert=True)
        await show_text_settings(callback)
    else:
        await callback.answer("❌ Ошибка при сбросе текста", show_alert=True)


@router.message(Command("timeout_settings"))
async def cmd_timeout_settings(message: Message, state: FSMContext):
    """Команда для доступа к настройкам таймаута"""
    await state.clear()
    await _show_timeout_main_menu(message)
