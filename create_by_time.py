import asyncio
import math
import re

import requests
from LOLZTEAM.API import Forum, Market
from aiogram import types, F, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
from config import token, secret
from keyboards import cbtkey

admin_ids=config.ADMIN_IDS
router_two=Router()
market = Market(token=token, language="en")
forum = Forum(token=token, language="en")

class RepeatForm(StatesGroup):
    waiting_for_interval = State()

class Form(StatesGroup):
    waiting_for_link = State()
    waiting_for_other = State()

tasks = {}
repeat_data = {}  # Хранилище данных для повторяющихся задач

@router_two.message(F.text == '📄 Создавать розыгрыш каждые X дней')
async def start_repeat_command(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_ids:

        await message.reply("Укажите интервал в днях, через который будет автоматически выполняться команда:")
        await state.set_state(RepeatForm.waiting_for_interval)

@router_two.message(StateFilter(RepeatForm.waiting_for_interval))
async def process_repeat_interval(message: types.Message, state: FSMContext):
    try:

        interval_days = int(message.text)
        await state.update_data(interval_days=interval_days)

        await message.reply(f"Повторение команды установлено каждые {interval_days} дней.\nОтправьте ссылку на розыгрыш:")
        await state.set_state(Form.waiting_for_link)
    except ValueError:
        await message.answer("Введите число")
        await state.clear()

@router_two.message(StateFilter(Form.waiting_for_link))
async def get_link(message: types.Message, state: FSMContext):
    link = message.text
    pattern = re.search(r'threads/(\d+)', link)
    if pattern:
        await state.update_data(link=link)
        await message.reply(f"Введите сумму розыгрыша, срок розыгрыша, тип срока (minutes, hours, days)\nПример: 555, 2, hours")
        await state.set_state(Form.waiting_for_other)
    else:
        await message.reply("Похоже, вы ввели не ссылку")
        await state.clear()

@router_two.message(StateFilter(Form.waiting_for_other))
async def get_other(message: types.Message, state: FSMContext):
    try:
        other = message.text  # Получаем текст от пользователя
        parts = [part.strip() for part in other.split(",")]
        price, dateX, dateY = parts  # Распаковываем части
        if int(price)<500:
            await message.reply("Сумма розыгрыша не может быть меньше 500₽\nПопробуйте снова")
            await state.clear()
        elif dateY not in ('minutes', 'hours', 'days'):
            await message.reply("Тип даты должен быть одним из следующего: minutes, hours, days\nПопробуйте снова.")
            await state.clear()
        elif int(dateX)>3 and dateY=='days':
            await message.reply('Срок розыгрыша не может быть больше, чем 3 days.')
            await state.clear()
        else:
            await state.update_data(price=price, dateX=dateX, dateY=dateY)
            user_data = await state.get_data()
            link = user_data.get('link')
            await message.reply(
                f"Содержание розыгрыша: {link}\nprice: {price}₽\nСрок: {dateX} {dateY}\nСоздавать?",
                reply_markup=cbtkey()
            )
            
            # Извлекаем ID темы из ссылки
            match = re.search(r'threads/(\d+)', link)
            if not match:
                await message.reply("Невозможно извлечь ID темы из ссылки. Проверьте правильность URL.")
                return

            thread_id = match.group(1)
            url = f"https://api.zelenka.guru/threads/{thread_id}"
            headers = {"authorization": f"Bearer {token}"}

            # Выполняем запрос к API для получения данных о теме
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                await message.reply(f"Ошибка при запросе к API: {response.status_code}")
                await state.clear()
                
                return

            # Проверяем наличие нужных данных в ответе
            json_data = response.json()       
            # Извлекаем информацию о теме
            title = json_data['thread']['thread_title']
            body = json_data['thread']['first_post']['post_body']
            await state.update_data(title=title, body=body)

            # Проверяем структуру thread_tags
            thread_tags = json_data['thread']['thread_tags']
            if isinstance(thread_tags, dict):
                tags = list(thread_tags.values())  # Если это список, просто используем его напрямую
            else:
                tags = []  # Если нет тегов, используем пустой список
            await state.update_data(tags=tags)
    except requests.exceptions.RequestException as req_err:
        await message.reply(f"Ошибка при выполнении запроса: {req_err}")
        print(req_err)
        await state.clear()
    except ValueError as val_err:
        await message.reply(f"Ошибка при обработке данных: {val_err}")
        await state.clear()
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")
        print(str(e))
        await state.clear()

@router_two.callback_query(F.data.in_({'cbtapprove_', 'cbtreject_'}))
# Создание розыгрыша и его повторение
async def da(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные для розыгрыша
    action = callback_query.data
    user_data = await state.get_data()
    title = user_data.get('title')
    body = user_data.get('body')
    price = user_data.get('price')
    dateX = user_data.get('dateX')
    dateY = user_data.get('dateY')
    tags = user_data.get('tags')
    if action=='cbtapprove_':
        try:
            price = int(price)
            like_count = max(200, min(math.floor(price/10), 4000))
            await asyncio.sleep(2)
            print(price, body, dateX, dateY, title, tags )
            response = forum.threads.contests.money.create_by_time(
                post_body=body, prize_data_money=price,
                count_winners=1, length_value=dateX, length_option=dateY,
                require_like_count=1, require_total_like_count=like_count, secret_answer=secret,
                tags=tags, title=title)
            response_data = response.json()
            if 'errors' in response_data:
                error = '\n'.join(response_data['errors'])
                await callback_query.message.edit_text(f'Произошла ошибка:\n{error}')
            else:
                thread_id = response.json()["thread"]["links"]["permalink"]
                print(f"Розыгрыш {thread_id} успешно создан!")
                await callback_query.message.edit_text(f"Розыгрыш успешно создан\n{thread_id}")
                await schedule_repeating_da(admin_ids)          
        except Exception as e:
            await callback_query.message.edit_text(f"Произошла ошибка: {e}")
    elif action=='cbtreject_':
        await callback_query.message.edit_text("Создание розыгрыша отменено")

# Повторяющаяся задача для выполнения команды через X дней
async def repeat_da_command(message, admin_ids, state: FSMContext):
    try:
        user_data = await state.get_data()
        interval_days = user_data.get('interval_days')
        user_id = message.from_user.id
        while True:
            await asyncio.sleep(interval_days * 86400)  # Интервал в днях
            await da(message, admin_ids, user_id)  # Выполнение команды для пользователя
    except asyncio.CancelledError:
        await message.reply("Повторение команды остановлено.")
        return
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

# Планирование повторяющейся задачи
async def schedule_repeating_da(message: types.Message, admin_ids, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    interval_days = user_data.get('interval_days')
    # Создаем новую повторяющуюся задачу
    task = asyncio.create_task(repeat_da_command(message, admin_ids))
    tasks[user_id] = task
    await message.reply(f"Команда будет повторяться каждые {interval_days} дня(ей).\nОтменить задачу - /cancel")

@router_two.message(F.text == 'Нет')
async def net(message: types.Message):
    await message.reply("Создание розыгрыша отменено")

# Отмена повторяющейся задачи
@router_two.message(Command('cancel'))
async def cancel_repeating_da(message: types.Message):
    user_id = message.from_user.id

    if user_id in tasks:
        task = tasks[user_id]
        print(task)
        if not task.done():
            task.cancel()  # Отменяем задачу
            await message.reply("Повторение команды успешно остановлено.")
        else:
            await message.reply("Задача уже завершена.")
    else:
        await message.reply("Нет активных задач для остановки.")

@router_two.message(Command('active'))
async def cancel_repeating_da(message: types.Message):
    user_id = message.from_user.id

    if user_id in tasks:
        task = tasks[user_id]
        print(task)
        await message.answer(str(task))

