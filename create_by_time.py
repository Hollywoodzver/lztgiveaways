import re
from aiogram.fsm.context import FSMContext
import requests
from LOLZTEAM.API import Forum, Market
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter, Command

import asyncio
from config import token, secret
from LOLZTEAM.API import Forum, Market
from keyboards import get_main_keyboard, get_time_keyboard
import config

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
        global interval_days
        interval_days = int(message.text)
        await state.update_data(interval_days=interval_days)

        await message.reply(f"Повторение команды установлено каждые {interval_days} дней.\nОтправьте ссылку на розыгрыш:")
        await state.set_state(Form.waiting_for_link)
    except ValueError:
        await message.answer("Введите число")
        await state.clear()

@router_two.message(StateFilter(Form.waiting_for_link))
async def get_link(message: types.Message, state: FSMContext):
    global link
    link = message.text
    pattern = re.search(r'threads/(\d+)', link)
    
    if pattern:
        await state.update_data(link=link)
        await message.reply(f"Введите сумму розыгрыша и срок:\nПример: 555, 2, hours")
        await state.set_state(Form.waiting_for_other)
    else:
        await message.reply("Похоже, вы ввели не ссылку")
        await state.clear()

@router_two.message(StateFilter(Form.waiting_for_other))
async def get_other(message: types.Message, state: FSMContext):
    global dateX, dateY
    try:
        other = message.text  # Получаем текст от пользователя
        parts = [part.strip() for part in other.split(",")]

        global price
        price, dateX, dateY = parts  # Распаковываем части
        await state.clear()  # Завершаем состояние
        if int(price)<500:
            await message.reply("Сумма розыгрыша не может быть меньше 500₽\nПопробуйте снова")
        elif dateY not in ('minutes', 'hours', 'days'):
            await message.reply("Тип даты должен быть одним из следующего: minutes, hours, days\nПопробуйте снова.")

        elif int(dateX)>3 and dateY=='days':
            await message.reply('Срок розыгрша не может быть больше, чем 3 days.')
        else:
            # Сохраняем данные в FSMContext
            user_data = await state.get_data()
       # Продолжаем диалог с пользователем
            await message.reply(
                f"Содержание розыгрыша: {link}\nprice: {price}₽\nСрок: {dateX} {dateY}\nСоздавать?",
                reply_markup=get_time_keyboard()
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
                await message.reply(f"Ошибка при запросе к API: {response.status_code}", reply_markup=get_main_keyboard())
                await state.finish
                
                return

            # Проверяем наличие нужных данных в ответе
            json_data = response.json()

            global body, title
            # Извлекаем информацию о теме
            title = json_data['thread']['thread_title']
            body = json_data['thread']['first_post']['post_body']

            # Проверяем структуру thread_tags
            thread_tags = json_data['thread']['thread_tags']
            global tags
            if isinstance(thread_tags, dict):
                tags = list(thread_tags.values())  # Если это список, просто используем его напрямую
            else:
                tags = []  # Если нет тегов, используем пустой список

            await state.clear()
    except requests.exceptions.RequestException as req_err:
        await message.reply(f"Ошибка при выполнении запроса: {req_err}")
        print(req_err)
        await state.finish()
    except ValueError as val_err:
        await message.reply(f"Ошибка при обработке данных: {val_err}")
        print(val_err)
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")
        print(str(e))
        await state.clear()

@router_two.message(F.text == 'Да, создавать')
# Создание розыгрыша и его повторение
async def da(message: types.Message, user_id=None, state=FSMContext):
    # Получаем данные для розыгрыша
   
    try:
        await asyncio.sleep(2)
        print(price, body, dateX, dateY, title, tags )
        response = response = forum.threads.contests.money.create_by_time(
            post_body=body, prize_data_money=price,
            count_winners=1, length_value=dateX, length_option=dateY,
            require_like_count=1, require_total_like_count=50, secret_answer=secret,
            tags=tags, title=title
            )
 
        thread_id = response.json()["thread"]["links"]["permalink"]
        await message.reply(f"Розыгрыш успешно создан\n{thread_id}", reply_markup=get_main_keyboard())
        await schedule_repeating_da(message, admin_ids)
    except Exception as e:
        if 'errors' in response.json():
            await message.reply(response.json()['errors'], reply_markup=get_main_keyboard())
        else:
            await message.reply(f"Произошла ошибка: {e}", reply_markup=get_main_keyboard())

# Повторяющаяся задача для выполнения команды через X дней
async def repeat_da_command(message, admin_ids):
    try:
        user_id = message.from_user.id
        while True:
            await asyncio.sleep(interval_days * 86400)  # Интервал в днях
            await da(message, admin_ids, user_id)  # Выполнение команды для пользователя
    except asyncio.CancelledError:
        await message.reply("Повторение команды остановлено.")
        return
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}", reply_markup=get_main_keyboard())

# Планирование повторяющейся задачи
async def schedule_repeating_da(message: types.Message, admin_ids):
    user_id = message.from_user.id


    # Создаем новую повторяющуюся задачу
    task = asyncio.create_task(repeat_da_command(message, admin_ids))
    tasks[user_id] = task
    await message.reply(f"Команда будет повторяться каждые {interval_days} дня(ей).", reply_markup=get_main_keyboard())


# Отмена повторяющейся задачи
@router_two.message(Command('/cancel'))
async def cancel_repeating_da(message: types.Message):
    user_id = message.from_user.id

    if user_id in tasks:
        task = tasks[user_id]
        print(task)
        if not task.done():
            task.cancel()  # Отменяем задачу
            await message.reply("Повторение команды успешно остановлено.",reply_markup=get_main_keyboard())
        else:
            await message.reply("Задача уже завершена.", reply_markup=get_main_keyboard())
    else:
        await message.reply("Нет активных задач для остановки.", reply_markup=get_main_keyboard())

@router_two.message(F.text == 'Нет')
async def net(message: types.Message, admin_ids):
    await message.reply("Создание розыгрыша отменено", reply_markup=get_main_keyboard())
