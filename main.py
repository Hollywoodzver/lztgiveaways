
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config

from handlers import router
from create_by_time import router_two
from mass_creation import ml
from createfrombb import r

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.API_TOKEN)  # Используем API_TOKEN из config.py
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


dp.include_router(router)
dp.include_router(router_two)
dp.include_router(ml)
dp.include_router(r)
async def main():
    # Запуск polling
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
