from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

from filters.admin_filter import AdminFilter, CouriersFilter
from keyboards.admins.menu_keyboard import get_admin_menu_keyboard
from keyboards.admins.menu_keyboard import get_courier_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()

admin_router = Router()
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

courier_router = Router()
courier_router.message.filter(CouriersFilter())
courier_router.callback_query.filter(CouriersFilter())

router.include_router(admin_router)
router.include_router(courier_router)


@admin_router.message(Command("start"))
async def cmd_admin_start(message: Message):
    """
    Обработчик команды /start для администраторов.
    Показывает главное меню администратора.
    """
    user_id = message.from_user.id
    username = message.from_user.username

    logger.info(f"Admin {user_id} (@{username}) opened admin menu")

    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        f"Вы вошли как администратор. Выберите действие из меню ниже:",
        reply_markup=get_admin_menu_keyboard()
    )


@courier_router.message(Command("start"))
async def cmd_courier_start(message: Message):
    """
    Обработчик команды /start для курьеров.
    Показывает главное меню курьера.
    """
    user_id = message.from_user.id
    username = message.from_user.username

    logger.info(f"Courier {user_id} (@{username}) opened courier menu")

    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        f"Вы вошли как курьер. Выберите действие из меню ниже:",
        reply_markup=get_courier_menu_keyboard()
    )
