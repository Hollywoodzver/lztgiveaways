import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from handlers import register_handlers 
from create_by_time import register_repeat_handlers
import config 



logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.API_TOKEN)  # Используем API_TOKEN из config.py
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

register_handlers(dp, config.ADMIN_IDS)  # Используем ADMIN_IDS из config.py
register_repeat_handlers(dp, config.ADMIN_IDS)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
