import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import TELEGRAM_BOT_TOKEN
from database.connection import init_db
from handlers import admin, client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def main():
    # 1. Initialize DB (create tables if they don't exist)
    logger.info("Initializing database...")
    await init_db()
    
    # 2. Initialize Bot and Dispatcher
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # 3. Include Routers
    # Register admin first so admin commands are checked first
    dp.include_router(admin.router)
    dp.include_router(client.router)
    
    # Set default bot commands menu
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Панель администратора")
    ])
    
    # 4. Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
