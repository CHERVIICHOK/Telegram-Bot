import logging
from typing import List, Dict, Any
from aiogram import Bot

from database.preorder_db import preorder_db
from database.users.database import add_to_cart
from database.users.warehouse_connection import get_product_by_id

import os

logger = logging.getLogger(__name__)


class PreorderProcessor:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def check_and_process_preorders(self, category: str, product_name: str, flavor: str,
                                          warehouse_product_id: int):
        """Проверить и обработать предзаказы при поступлении товара"""
        try:
            # Получаем товар из предзаказов
            preorder_product = preorder_db.get_product_details(category, product_name, flavor)

            if not preorder_product:
                return

            # Получаем всех пользователей с предзаказом на этот товар
            users_with_preorders = self._get_users_with_preorder(preorder_product['id'])

            if not users_with_preorders:
                return

            # Получаем информацию о товаре со склада
            warehouse_product = get_product_by_id(warehouse_product_id)
            if not warehouse_product:
                return

            # Обрабатываем каждого пользователя
            for user_id in users_with_preorders:
                await self._process_user_preorder(
                    user_id,
                    preorder_product,
                    warehouse_product,
                    warehouse_product_id
                )

            # Деактивируем товар в предзаказах
            preorder_db.delete_preorder_product(preorder_product['id'])

        except Exception as e:
            logger.error(f"Ошибка при обработке предзаказов: {e}")

    def _get_users_with_preorder(self, product_id: int) -> List[int]:
        """Получить список пользователей с предзаказом на товар"""
        import sqlite3
        users = []
        try:
            with sqlite3.connect(preorder_db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT user_id 
                    FROM user_preorders 
                    WHERE product_id = ? AND status = 'active'
                ''', (product_id,))
                users = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей с предзаказом: {e}")
        return users

    async def _process_user_preorder(self, user_id: int, preorder_product: Dict[str, Any],
                                     warehouse_product: tuple, warehouse_product_id: int):
        """Обработать предзаказ конкретного пользователя"""
        try:
            if add_to_cart(user_id, warehouse_product_id, quantity=1):
                # Отправляем уведомление пользователю
                await self._send_notification(
                    user_id,
                    preorder_product,
                    warehouse_product,
                    warehouse_product_id
                )

                # Удаляем предзаказ
                preorder_db.cancel_preorder(user_id, preorder_product['id'])

        except Exception as e:
            logger.error(f"Ошибка при обработке предзаказа пользователя {user_id}: {e}")

    async def _send_notification(self, user_id: int, preorder_product: Dict[str, Any],
                                 warehouse_product: tuple, warehouse_product_id: int):
        """Отправить уведомление пользователю о поступлении товара"""
        try:
            (product_id, category, product_name, product_full_name,
             flavor, price, description, quantity, image_path) = warehouse_product

            text = (
                "🎉 <b>Отличная новость!</b>\n\n"
                f"Товар из вашего предзаказа поступил на склад:\n\n"
                f"📦 <b>{product_full_name}</b>\n"
                f"💰 Цена: {price} ₽\n\n"
                "✅ Товар автоматически добавлен в вашу корзину.\n"
                "Вы можете оформить заказ в любое удобное время!"
            )

            # Создаем клавиатуру с кнопками
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton

            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text="🛒 Перейти в корзину",
                    callback_data="cart:show"
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="📦 Посмотреть товар",
                    callback_data=f"catalog:{category}:{product_name}:{warehouse_product_id}"
                )
            )

            # Если есть изображение товара, отправляем с фото
            if image_path and os.path.exists(image_path):
                try:
                    from aiogram.types import FSInputFile
                    photo = FSInputFile(image_path)
                    await self.bot.send_photo(
                        user_id,
                        photo=photo,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке фото: {e}")
                    # Если не удалось отправить с фото, отправляем текстом
                    await self.bot.send_message(
                        user_id,
                        text,
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
            else:
                await self.bot.send_message(
                    user_id,
                    text,
                    parse_mode="HTML",
                    reply_markup=builder.as_markup()
                )

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")


preorder_processor = None


def init_preorder_processor(bot: Bot):
    """Инициализировать процессор предзаказов"""
    global preorder_processor
    preorder_processor = PreorderProcessor(bot)
    return preorder_processor
