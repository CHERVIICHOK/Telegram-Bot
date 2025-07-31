from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.users.keyboards import main_menu_keyboard

router = Router()


@router.message(Command("menu"))
async def command_menu_handler(message: Message) -> None:
    """
    Обработчик команды /menu.
    Открывает главное меню.
    """
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard)
