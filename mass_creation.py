import re
from aiogram.fsm.context import FSMContext
import requests
from LOLZTEAM.API import Forum, Market
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter, Command
import math
import asyncio
from config import token, secret
from LOLZTEAM.API import Forum, Market
from keyboards import get_main_keyboard, get_time1_keyboard
import config
 
admin_ids=config.ADMIN_IDS
ml=Router()
market = Market(token=token, language="en")
forum = Forum(token=token, language="en")

tasks = {}
repeat_data = {}  # Хранилище данных для повторяющихся задач

class RepeatForm(StatesGroup):
    waiting_for_count = State()

class Form(StatesGroup):
    
    waiting_for_link1 = State()
    waiting_for_other1 = State()

@ml.message(F.text == '📄 Создать несколько розыгрышей')
async def many_command(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_ids:
        await message.answer("Укажите количество розыгрышей")
        await state.set_state(RepeatForm.waiting_for_count)

@ml.message(StateFilter(RepeatForm.waiting_for_count))
async def count(message: types.Message, state: FSMContext):
    global count_give
    try:
        count_give = int(message.text)
        await state.update_data(count_give=count_give)

        await message.reply(f"Колиство розыгрышей - {count_give}\nОтправьте ссылку на тему, откуда скопируется информация:")
        await state.set_state(Form.waiting_for_link1)
    except ValueError:
        await message.answer("Введите число")
        await state.clear()

@ml.message(StateFilter(Form.waiting_for_link1))
async def link_get(message: types.Message, state: FSMContext):
    global link
    link = message.text
    pattern = re.search(r'threads/(\d+)', link)  
    if pattern:
        await state.update_data(link=link)
        await message.reply(f"Введите сумму розыгрыша и срок:\nПример: 555, 2, hours")
        await state.set_state(Form.waiting_for_other1)
    else:
        await message.reply("Похоже, вы ввели не ссылку")
        await state.clear()

@ml.message(StateFilter(Form.waiting_for_other1))
async def other(message: types.Message, state: FSMContext):
    global dateX, dateY, price
    try:
        other = message.text
        parts = [part.strip() for part in other.split(",")]

        price, dateX, dateY = parts
        await state.clear()
        if int(price)<500:
            await message.reply("Сумма розыгрышей не может быть меньше 500₽\nПопробуйте сначала")
        elif dateY not in ('minutes', 'hours', 'days'):
            await message.reply("Тип даты должен быть одним из следующего: minutes, hours, days\nПопробуйте снова.")
        elif int(dateX)>3 and dateX=='days':
            await message.reply("Срок розыгрша не может быть больше, чем 3 days.\nПопробуйте снова.")
        else:
            like_count=math.floor(int(price)/10)
            if like_count>2000:
                like_count=2000
            await message.reply(
                f"Количество розыгрышей: {count_give}\nСодержание розыгрыша: {link}\nprice: {price}₽\nСрок: {dateX} {dateY}\nНеобходимо симпатий для участия: {like_count}\nСоздавать(действие нельзя отменить)?",
                reply_markup=get_time1_keyboard()
            )

            # Извлекаем ID темы из ссылки
            match = re.search(r'threads/(\d+)', link)
            if not match:
                await message.reply("Невозможно извлечь ID темы из ссылки. Проверьте правильность URL.", reply_markup=get_main_keyboard())
                return

            thread_id = match.group(1)
            url = f"https://api.zelenka.guru/threads/{thread_id}"
            headers = {"authorization": f"Bearer {token}"}

            # Выполняем запрос к API для получения данных о теме
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                await message.reply(f"Ошибка при запросе к API: {response.status_code}", reply_markup=get_main_keyboard())
                await state.clear()
                
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

@ml.message(F.text == 'Да, создавать')
async def da1(message: types.Message):
    response = None
    try:
        count = 0
        await message.reply("Розыгрыши скоро начнут создаваться. Ожидайте", reply_markup=get_main_keyboard())
        while count < count_give:
            count += 1
            await asyncio.sleep(62)
            print(f"Цена: {price},\nСрок: {dateX, dateY},\nЗаголовок: {title},\nТеги: {tags}")
            response = forum.threads.contests.money.create_by_time(
                post_body=body, prize_data_money=price,
                count_winners=1, length_value=dateX, length_option=dateY,
                require_like_count=1, require_total_like_count=50, secret_answer=secret,
                tags=tags, title=title
                )
            
            # Проверяем ответ
            if response:
                thread_id = response.json()["thread"]["links"]["permalink"]
                await message.reply(f"Розыгрыш успешно создан\n{thread_id}\nОсталось {count_give-count}")
            else:
                await message.reply("Не удалось создать розыгрыш: ответ пустой.")
        if count == count_give:
            await message.reply(f"Все розыгрыши успешно созданы!")
            

    except Exception as e:
        if response and response.json().get('errors'):
            await message.reply(response.json()['errors'], reply_markup=get_main_keyboard())
        else:
            await message.reply(f"Произошла ошибка: {e}", reply_markup=get_main_keyboard())



@ml.message(F.text == "Отмена")
async def net0(message: types.Message):
    await message.reply("Создание розыгрышей отменено", reply_markup=get_main_keyboard())

   