import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from database.admins.staff_db import create_staff_table
from database.users.reviews_db import create_product_reviews_table, create_delivery_comments_table

from handlers.admins.order_status import router as admin_order_status_router
from handlers.admins.start import router as admin_start_router
from handlers.admins.manage_products import router as admin_manage_products_router
from handlers.admins.broadcast import router as admin_broadcast_router

from handlers.users import catalog, start_handler, main_menu_handler
from database.users.database_connection import create_users_table, create_connection, close_connection
from database.users.favorites_db import create_favorites_table
from handlers.users.cart import router as cart_router
from handlers.users.order import router as order_router
from database.users.database import create_orders_table
from handlers.users.profile_handlers import profile_router
from database.users.profile_db import create_profile_tables
from database.admins.image_db import create_product_images_table
from handlers.admins.stock_thresholds import router as stock_thresholds_router, init_stock_thresholds_tables
from handlers.admins.process_order import router as process_order_router
from handlers.admins.statistics_collection import router as admin_statistics_router
from handlers.users.help_handler import router as help_router
from handlers.admins.manage_images import router as manage_images_router
from handlers.admins.manage_staff import router as staff_router
from handlers.users.favorites import router as favorites_router
from handlers.admins import order_timeout
from handlers.admins.client_contact import router as client_contact_router
from handlers.users.about_me_handlers import router as about_me_router
from handlers.users.preorder_handlers import router as preorder_router
from handlers.admins.preorder_admin_handlers import router as preorder_admin_router
from handlers.users.discounts_handler import discounts_router
from handlers.admins.discounts_admin_handler import admin_discounts_router
from handlers.admins.actions_admin_handler import actions_admin_router


from utils.preorder_processor import init_preorder_processor


logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=TOKEN)
    init_preorder_processor(bot)
    dp = Dispatcher()

    create_users_table()
    create_favorites_table()
    create_staff_table()
    create_profile_tables()
    init_stock_thresholds_tables()
    create_product_images_table()
    create_product_reviews_table()
    create_delivery_comments_table()

    conn = create_connection()
    if conn:
        create_orders_table(conn)
        close_connection(conn)

    dp.include_router(admin_start_router)
    dp.include_router(admin_order_status_router)
    dp.include_router(admin_manage_products_router)
    dp.include_router(admin_broadcast_router)
    dp.include_router(stock_thresholds_router)
    dp.include_router(process_order_router)
    dp.include_router(help_router)
    dp.include_router(actions_admin_router)

    dp.include_router(catalog.router)
    dp.include_router(start_handler.router)
    dp.include_router(main_menu_handler.router)
    dp.include_router(cart_router)
    dp.include_router(order_router)
    dp.include_router(profile_router)
    dp.include_router(admin_statistics_router)
    dp.include_router(manage_images_router)
    dp.include_router(staff_router)
    dp.include_router(favorites_router)
    dp.include_router(order_timeout.router)
    dp.include_router(client_contact_router)
    dp.include_router(about_me_router)
    dp.include_router(preorder_router)
    dp.include_router(preorder_admin_router)
    dp.include_router(discounts_router)
    dp.include_router(admin_discounts_router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
