from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from keyboards.admins.order_status_keyboard import (
    get_status_category_keyboard,
    get_orders_keyboard,
    get_order_status_keyboard,
    get_confirm_delete_keyboard
)
from database.admins.orders_bd import (
    get_undelivered_orders,
    get_orders_by_status_category,
    get_order_by_id,
    update_order_status
)
from utils.order_timeout_manager import order_timeout_manager
from utils.status_utils import format_order_info, ORDER_STATUS, STATUS_CATEGORIES
from filters.admin_filter import AdminFilter, CouriersFilter
from keyboards.admins.menu_keyboard import get_admin_menu_keyboard, get_courier_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()


courier_router = Router()
courier_router.message.filter(CouriersFilter())
courier_router.callback_query.filter(CouriersFilter())

admin_router = Router()
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

router.include_router(courier_router)
router.include_router(admin_router)


class OrderStatusStates(StatesGroup):
    selecting_category = State()
    selecting_order = State()
    selecting_status = State()
    confirming_deletion = State()


@router.callback_query(F.data == "cmd_change_order_status")
async def process_change_order_status(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку изменения статуса заказа в главном меню"""
    is_admin = await AdminFilter().__call__(callback)
    is_courier = await CouriersFilter().__call__(callback)

    user_role = "admin" if is_admin else "courier" if is_courier else "unknown"
    logger.info(f"{user_role.capitalize()} {callback.from_user.id} selected order status change from menu")

    await state.update_data(user_role=user_role)
    await state.set_state(OrderStatusStates.selecting_category)

    keyboard = get_status_category_keyboard()
    await callback.message.edit_text(
        "Выберите категорию заказов для изменения статуса:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработчик команды изменения статуса заказа
@router.message(Command("change_order_status"))
async def cmd_change_order_status(message: Message, state: FSMContext):
    logger.info(f"Admin {message.from_user.id} requested order status change")

    await state.set_state(OrderStatusStates.selecting_category)

    keyboard = get_status_category_keyboard()
    await message.answer(
        "Выберите категорию заказов для изменения статуса:",
        reply_markup=keyboard
    )


# Обработчик выбора категории статусов
@router.callback_query(OrderStatusStates.selecting_category, F.data.startswith("status_category:"))
async def process_status_category_selection(callback: CallbackQuery, state: FSMContext):
    category_key = callback.data.split(":")[1]
    logger.info(f"Admin {callback.from_user.id} selected status category {category_key}")

    await state.update_data(selected_category=category_key)

    orders, total_orders = get_orders_by_status_category(category_key, page=1)

    if not orders:
        category_name = STATUS_CATEGORIES[category_key]["name"]
        await callback.message.edit_text(
            f"В категории '{category_name}' нет заказов. Выберите другую категорию:",
            reply_markup=get_status_category_keyboard()
        )
        await callback.answer()
        return

    await state.set_state(OrderStatusStates.selecting_order)
    await state.update_data(current_page=1)

    keyboard = get_orders_keyboard(orders, page=1, total_orders=total_orders, category_key=category_key)
    await callback.message.edit_text(
        f"Заказы категории '{STATUS_CATEGORIES[category_key]['name']}'. Выберите заказ для изменения статуса:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработчик пагинации списка заказов по категории
@router.callback_query(F.data.startswith("cat_order_list:"))
async def process_category_order_list_pagination(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    category_key = parts[1]
    page = int(parts[2])

    logger.info(f"Admin {callback.from_user.id} navigated to order list page {page} in category {category_key}")

    orders, total_orders = get_orders_by_status_category(category_key, page=page)

    await state.update_data(current_page=page)

    keyboard = get_orders_keyboard(orders, page=page, total_orders=total_orders, category_key=category_key)
    await callback.message.edit_text(
        f"Заказы категории '{STATUS_CATEGORIES[category_key]['name']}'. Выберите заказ для изменения статуса:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработчик возврата к выбору категории
@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Admin {callback.from_user.id} returned to status categories")

    await state.set_state(OrderStatusStates.selecting_category)

    keyboard = get_status_category_keyboard()
    await callback.message.edit_text(
        "Выберите категорию заказов для изменения статуса:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработчик выбора заказа
@router.callback_query(F.data.startswith("order_status:"))
async def process_order_selection(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    logger.info(f"Admin {callback.from_user.id} selected order #{order_id} for status change")

    order = get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    await state.set_state(OrderStatusStates.selecting_status)
    await state.update_data(order_id=order_id)

    order_info = format_order_info(order)

    keyboard = get_order_status_keyboard(order_id)
    await callback.message.edit_text(
        f"{order_info}\n\nВыберите новый статус для заказа:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработчик возврата к списку заказов
@router.callback_query(F.data == "back_to_orders")
async def back_to_orders_list(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Admin {callback.from_user.id} returned to order list")

    data = await state.get_data()
    current_page = data.get("current_page", 1)
    selected_category = data.get("selected_category")

    await state.set_state(OrderStatusStates.selecting_order)

    if selected_category:
        orders, total_orders = get_orders_by_status_category(selected_category, page=current_page)
        keyboard = get_orders_keyboard(
            orders,
            page=current_page,
            total_orders=total_orders,
            category_key=selected_category
        )
        await callback.message.edit_text(
            f"Заказы категории '{STATUS_CATEGORIES[selected_category]['name']}'. Выберите заказ для изменения статуса:",
            reply_markup=keyboard
        )
    else:
        orders, total_orders = get_undelivered_orders(page=current_page)
        keyboard = get_orders_keyboard(orders, page=current_page, total_orders=total_orders)
        await callback.message.edit_text(
            "Выберите заказ для изменения статуса:",
            reply_markup=keyboard
        )

    await callback.answer()


# Обработчик выбора нового статуса
@router.callback_query(F.data.startswith("set_status:"))
async def process_status_selection(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status = parts[2]

    state_data = await state.get_data()
    user_role = state_data.get("user_role", "unknown")

    logger.info(f"{user_role.capitalize()} {callback.from_user.id} changing order #{order_id} status to {new_status}")

    order = get_order_by_id(order_id)
    user_order_id = order['user_order_id']

    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    old_status = order.get("status")
    user_id = order.get("user_id")  # ID пользователя, сделавшего заказ

    success = update_order_status(order_id, new_status)

    if success:
        old_status_text = ORDER_STATUS.get(old_status, "Неизвестный статус")
        new_status_text = ORDER_STATUS.get(new_status, "Неизвестный статус")

        await callback.answer(f"Статус заказа #{order_id} изменен на '{new_status_text}'", show_alert=True)

        if user_id:
            try:
                await callback.bot.send_message(
                    user_id,
                    f"📬 Новое уведомление от бота!\n\n Статус вашего заказа #{user_order_id} изменен с '{old_status_text}' на '{new_status_text}'.",
                    parse_mode='HTML'
                )
                logger.info(f"Notification sent to user {user_id} about order #{order_id} status change")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")

        await state.clear()

        menu_keyboard = get_admin_menu_keyboard() if user_role == "admin" else get_courier_menu_keyboard()
        role_text = "администратора" if user_role == "admin" else "курьера"

        await callback.message.edit_text(
            f"✅ Статус заказа #{order_id} успешно изменен на '{new_status_text}'.\n\n"
            f"Вы были перенаправлены в главное меню {role_text}.",
            reply_markup=menu_keyboard
        )

        if old_status == 'processing' and new_status != 'processing':
            await order_timeout_manager.cancel_timer(order_id)

    else:
        await callback.answer("Ошибка при изменении статуса заказа!", show_alert=True)


# Первый этап: запрос подтверждения
@router.callback_query(F.data.startswith("delete_order:"))
async def process_delete_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    order = get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить заказ #{order_id}? ⚠️\n"
        "Это действие необратимо.",
        reply_markup=get_confirm_delete_keyboard(order_id)
    )
    await callback.answer()


# Второй этап: подтверждение удаления
@router.callback_query(F.data.startswith("confirm_delete_order:"))
async def process_confirm_delete_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    logger.info(f"Admin {callback.from_user.id} confirmed deletion of order #{order_id}")

    order = get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    user_id = order.get("user_id")
    user_order_id = order.get("user_order_id")

    from database.admins.orders_bd import delete_order_by_id
    success = delete_order_by_id(order_id)

    if success:
        if user_id:
            try:
                await callback.bot.send_message(
                    user_id,
                    f"📬 Новое уведомление от бота!\n\n"
                    f"Ваш заказ #{user_order_id} был удален администратором.",
                    parse_mode='HTML'
                )
                logger.info(f"Notification sent to user {user_id} about order #{order_id} deletion")
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")

        data = await state.get_data()
        selected_category = data.get("selected_category")
        current_page = data.get("current_page", 1)

        await state.set_state(OrderStatusStates.selecting_order)

        if selected_category:
            orders, total_orders = get_orders_by_status_category(selected_category, page=current_page)
            keyboard = get_orders_keyboard(
                orders,
                page=current_page,
                total_orders=total_orders,
                category_key=selected_category
            )
            await callback.message.edit_text(
                f"Заказ #{order_id} успешно удален.\n\n"
                f"Заказы категории '{STATUS_CATEGORIES[selected_category]['name']}'. Выберите заказ:",
                reply_markup=keyboard
            )
        else:
            orders, total_orders = get_undelivered_orders(page=current_page)
            keyboard = get_orders_keyboard(orders, page=current_page, total_orders=total_orders)
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} успешно удален.\n\n"
                f"Выберите заказ:",
                reply_markup=keyboard
            )

        await callback.answer(f"✅ Заказ #{order_id} успешно удален", show_alert=True)
    else:
        await callback.answer("Ошибка при удалении заказа!", show_alert=True)


# Третий этап: отмена удаления
@router.callback_query(F.data.startswith("cancel_delete_order:"))
async def process_cancel_delete_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected_category = data.get("selected_category")
    current_page = data.get("current_page", 1)

    await state.set_state(OrderStatusStates.selecting_order)

    if selected_category:
        orders, total_orders = get_orders_by_status_category(selected_category, page=current_page)
        keyboard = get_orders_keyboard(
            orders,
            page=current_page,
            total_orders=total_orders,
            category_key=selected_category
        )
        await callback.message.edit_text(
            f"Удаление заказа #{order_id} отменено.\n\n"
            f"Заказы категории '{STATUS_CATEGORIES[selected_category]['name']}'. Выберите заказ:",
            reply_markup=keyboard
        )
    else:
        orders, total_orders = get_undelivered_orders(page=current_page)
        keyboard = get_orders_keyboard(orders, page=current_page, total_orders=total_orders)
        await callback.message.edit_text(
            f"Удаление заказа #{order_id} отменено.\n\n"
            f"Выберите заказ:",
            reply_markup=keyboard
        )

    await callback.answer("Удаление отменено", show_alert=True)


# Обработчик для возврата в главное меню
@router.callback_query(F.data == "admin_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    is_admin = await AdminFilter().__call__(callback)
    is_courier = await CouriersFilter().__call__(callback)

    user_role = "admin" if is_admin else "courier" if is_courier else "unknown"
    logger.info(f"{user_role.capitalize()} {callback.from_user.id} returned to main menu")

    await state.clear()

    if is_admin:
        menu_keyboard = get_admin_menu_keyboard()
        menu_text = "администратора"
    elif is_courier:
        menu_keyboard = get_courier_menu_keyboard()
        menu_text = "курьера"
    else:
        menu_keyboard = get_admin_menu_keyboard()
        menu_text = ""

    await callback.message.edit_text(
        f"Вы вернулись в главное меню {menu_text}:",
        reply_markup=menu_keyboard
    )

    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
