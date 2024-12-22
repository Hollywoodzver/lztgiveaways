import math
import re
from aiogram.fsm.context import FSMContext
import requests
from LOLZTEAM.API import Forum, Market
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
import asyncio
import config
from config import token, secret
from keyboards import bbkey
from aiogram.filters import StateFilter, CommandStart
import logging


logging.basicConfig(level=logging.INFO)

r=Router()
admin_ids=config.ADMIN_IDS


class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_bbcode = State()  # Состояние для второго текста
    waiting_for_prices = State()

market = Market(token=token, language="en")
forum = Forum(token=token, language="en")

@r.message(F.text=="📄 Создать из bb-code")
async def first(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_ids:
        await message.reply("Отправьте заголовок розыгрыша")
        await state.set_state(Form.waiting_for_name)

@r.message(StateFilter(Form.waiting_for_name))
async def name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.reply("Отправьте bb-code розыгрыша(в нем может быть максимум 2 фото)")
    await state.set_state(Form.waiting_for_bbcode)

@r.message(StateFilter(Form.waiting_for_bbcode))
async def bbcode(message: types.Message, state: FSMContext):
    bbcode=message.text
    await state.update_data(bbcode=bbcode)
    await message.reply("Введите сумму розыгрыша, срок розыгрыша, тип срока (minutes, hours, days)\n\nПример: 555, 2, hours (Будет создан розыгрыш на 555₽, Сроком 2 часа)")
    await state.set_state(Form.waiting_for_prices)

@r.message(StateFilter(Form.waiting_for_prices))
async def prices(message: types.Message, state: FSMContext):
    prices_input = message.text
    try:
        parts = [part.strip() for part in prices_input.split(",")]
        price = parts[0]
        date = parts[-2]
        date2 = parts[-1]
        await state.update_data(price=price, date=date, date2=date2)
        user_data = await state.get_data()
        name = user_data.get('name')
        bbcode = user_data.get('bbcode')
        if isinstance(price, str) and not price.isdigit():
            await message.reply("Попробуйте сначала")
            await state.clear()
        elif int(price)<500:
            await message.reply("Минимальная сумма розыгрыша - 500 рублей.\nПопробуйте сначала")
            await state.clear()
        elif date2 not in ('minutes', 'hours', 'days'):
            await message.reply('Поддерживаемый формат: "minutes", "hours", "days".\nПопробуйте сначала')
            await state.clear()
        elif int(date) > 3 and date2=="days":
            await message.reply("Длительность розыгрыша не может быть больше 3 days.\nПопробуйте сначала")
            await state.clear()
        else:
            await message.reply(
                    f"Заголовок: <pre><code>{name}</code></pre>\nСодержание: <pre><code>{bbcode}</code></pre>price: {price}₽\nСрок розыгрыша: {date} {date2}\nСоздавать розыгрыш?", parse_mode=ParseMode.HTML, reply_markup=bbkey()
                    )
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}\nПопробуйте сначала")
        await state.clear()
    
@r.callback_query(F.data.in_({'bbapprove_', 'bbreject_'}))
async def bconf(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    user_data = await state.get_data()
    price = user_data.get('price')
    body = user_data.get('bbcode')
    date = user_data.get('date')
    date2 = user_data.get('date2')
    title1 = user_data.get('name')
    if action=='bbapprove_':
        try:
            await asyncio.sleep(2)
            like_count = max(200, min(math.floor(price/10), 4000))
            response = forum.threads.contests.money.create_by_time(post_body=body,prize_data_money=int(price), count_winners=1,
                                                                length_value=date, length_option=date2, require_like_count=1,
                                                                    require_total_like_count=like_count, secret_answer=secret, title=title1)
            print(response.json())
            response_data = response.json()
            
            thread_id = response.json()["thread"]["links"]["permalink"]
            print(f"Розыгрыш {thread_id} успешно создан!")
            await callback_query.message.edit_text(f"Розыгрыш успешно создан\n{thread_id}")
        except Exception as e:
            if 'errors' in response_data:
                errors = '\n'.join(response_data['errors'])
                await callback_query.message.edit_text(f"Ошибки в ответе: {errors}")
                await state.clear()
            else:
                await callback_query.message.edit_text(f'Произошла ошибка {e}')
                await state.clear()
    elif action=='bbreject_':
        await callback_query.message.edit_text("Создание розыгрыша отменено")
        await state.clear()
            


