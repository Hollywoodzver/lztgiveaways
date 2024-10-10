import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from handlers import register_handlers 


API_TOKEN = 'your bot token'
ADMIN_IDS = [123, 12345] #your admin ids

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


register_handlers(dp, ADMIN_IDS)
print('000000')
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)