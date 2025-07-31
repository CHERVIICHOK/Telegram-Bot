import asyncio
import logging
from typing import Dict
from aiogram import Bot

from database.admins.orders_bd import get_order_by_id
from database.admins.settings_db import get_order_processing_timeout, get_notification_interval, get_notification_text
from database.admins.staff_db import get_staff_by_role

logger = logging.getLogger(__name__)


class OrderTimeoutManager:
    """Менеджер для отслеживания таймаутов обработки заказов"""

    def __init__(self):
        self._active_timers: Dict[int, asyncio.Task] = {}
        self._notification_counts: Dict[int, int] = {}

    async def start_timer(self, order_id: int, bot: Bot):
        """Запускает таймер для отслеживания обработки заказа"""
        await self.cancel_timer(order_id)

        self._notification_counts[order_id] = 0

        task = asyncio.create_task(self._order_timeout_handler(order_id, bot))
        self._active_timers[order_id] = task
        logger.info(f"Started timeout timer for order #{order_id}")

    async def cancel_timer(self, order_id: int):
        """Отменяет таймер для заказа"""
        if order_id in self._active_timers:
            task = self._active_timers[order_id]
            if not task.done():
                task.cancel()
            del self._active_timers[order_id]

        if order_id in self._notification_counts:
            del self._notification_counts[order_id]

        logger.info(f"Cancelled timeout timer for order #{order_id}")

    async def _order_timeout_handler(self, order_id: int, bot: Bot):
        """Обработчик таймаута заказа с периодическими уведомлениями"""
        try:
            timeout_minutes = get_order_processing_timeout()
            interval_minutes = get_notification_interval()

            await asyncio.sleep(timeout_minutes * 60)

            while True:
                order = get_order_by_id(order_id)
                if not order:
                    logger.warning(f"Order #{order_id} not found for timeout check")
                    break

                if order['status'] == 'processing':
                    self._notification_counts[order_id] += 1
                    await self._send_timeout_notifications(order_id, order, bot)

                    await asyncio.sleep(interval_minutes * 60)
                else:
                    logger.info(f"Order #{order_id} has been processed, stopping notifications")
                    break

        except asyncio.CancelledError:
            logger.info(f"Timeout timer for order #{order_id} was cancelled")
        except Exception as e:
            logger.error(f"Error in timeout handler for order #{order_id}: {e}")
        finally:
            if order_id in self._active_timers:
                del self._active_timers[order_id]
            if order_id in self._notification_counts:
                del self._notification_counts[order_id]

    async def _send_timeout_notifications(self, order_id: int, order: dict, bot: Bot):
        """Отправляет уведомления курьерам о необработанном заказе"""
        try:
            timeout_minutes = get_order_processing_timeout()
            interval_minutes = get_notification_interval()
            notification_text = get_notification_text()

            notification_count = self._notification_counts.get(order_id, 1)
            elapsed_time = timeout_minutes + (notification_count - 1) * interval_minutes

            formatted_text = notification_text.format(
                order_id=order_id,
                elapsed_time=elapsed_time,
                notification_count=notification_count
            )

            if notification_count > 1:
                formatted_text += f"\n\n📢 Это уведомление #{notification_count}"

            couriers = get_staff_by_role(role="Курьер")
            courier_ids = [courier['telegram_id'] for courier in couriers if courier.get('is_active', 1)]

            sent_count = 0
            for courier_id in courier_ids:
                try:
                    await bot.send_message(
                        courier_id,
                        formatted_text,
                        parse_mode="HTML"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send timeout notification to courier {courier_id}: {e}")

            logger.info(
                f"Sent timeout notification #{notification_count} for order #{order_id} to {sent_count} couriers")

        except Exception as e:
            logger.error(f"Error sending timeout notifications for order #{order_id}: {e}")


order_timeout_manager = OrderTimeoutManager()
