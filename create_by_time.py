import asyncio
from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
import requests
import re
from config import token, secret
from LOLZTEAM.API import Forum, Market
from keyboards import get_main_keyboard, get_time_keyboard

market = Market(token=token, language="en")
forum = Forum(token=token, language="en")

class RepeatForm(StatesGroup):
    waiting_for_interval = State()

class Form(StatesGroup):
    waiting_for_link = State()
    waiting_for_other = State()

tasks = {}
repeat_data = {}  # Хранилище данных для повторяющихся задач

# Начало команды повторения
async def start_repeat_command(message: types.Message, admin_ids):
    if message.from_user.id in admin_ids:
        await message.reply("Укажите интервал в днях, через который будет автоматически выполняться команда:")
        await RepeatForm.waiting_for_interval.set()

# Обработка интервала
async def process_repeat_interval(message: types.Message, admin_ids, state: FSMContext):
    try:
        global interval_days
        interval_days = int(message.text)
        await state.update_data(interval_days=interval_days)

        await message.reply(f"Повторение команды установлено каждые {interval_days} дней.\nОтправьте ссылку на розыгрыш:")
        await Form.waiting_for_link.set()
    except ValueError:
        await message.answer("Введите число")
        await RepeatForm.waiting_for_interval.set()

# Получение ссылки
async def get_link(message: types.Message, state: FSMContext):
    link = message.text
    pattern = re.search(r'threads/(\d+)', link)

    if pattern:
        await state.update_data(link=link)
        await message.reply(f"Введите сумму розыгрыша и срок:\nПример: 555, 2, hours", parse_mode=ParseMode.MARKDOWN_V2)
        await Form.waiting_for_other.set()
    else:
        await message.reply("Похоже, вы ввели не ссылку")
        await Form.waiting_for_link.set()

# Получение остальных данных
async def get_other(message: types.Message, state: FSMContext, admin_ids):
    global dateX, dateY
    try:
        other = message.text  # Получаем текст от пользователя
        parts = [part.strip() for part in other.split(",")]

        global price
        price, dateX, dateY = parts  # Распаковываем части

        # Проверка на корректность числовых данных для цены и срока
        if not price.isdigit() or not dateX.isdigit():
            await message.reply("Сумма и срок должны быть числовыми значениями. Попробуйте заново.")
            return

        # Сохраняем данные в FSMContext
        await state.update_data(price=price, dateX=dateX, dateY=dateY)

        # Получаем ссылку, сохраненную на предыдущем этапе
        user_data = await state.get_data()
        link = user_data.get('link')

        if not link:
            await message.reply("Ссылка на розыгрыш не найдена. Попробуйте заново.")
            return

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
            await message.reply(f"Ошибка при запросе к API: {response.status_code}")
            return

        # Проверяем наличие нужных данных в ответе
        json_data = response.json()
        if 'thread' not in json_data or 'first_post' not in json_data['thread']:
            await message.reply("Ошибка: данные темы не найдены.")
            return
        global body, title
        # Извлекаем информацию о теме
        title = json_data['thread']['thread_title']
        body = json_data['thread']['first_post']['post_body']

        # Проверяем структуру thread_tags
        thread_tags = json_data['thread']['thread_tags']
        global tags
        if isinstance(thread_tags, list):
            tags = thread_tags  # Если это список, просто используем его напрямую
        elif isinstance(thread_tags, dict):
            tags = list(thread_tags.values())  # Если это словарь, берем значения
        else:
            tags = []  # Если нет тегов, используем пустой список

        # Сохраняем дополнительные данные
        await state.update_data(title=title, body=body, tags=tags)

        # Сохраняем все данные в `repeat_data`, чтобы использовать их в повторяющейся задаче
        repeat_data[message.from_user.id] = {
            'link': link,
            'price': price,
            'dateX': dateX,
            'dateY': dateY,
            'body': body,
            'title': title,
            'tags': tags
        }

    except requests.exceptions.RequestException as req_err:
        await message.reply(f"Ошибка при выполнении запроса: {req_err}")
    except ValueError as val_err:
        await message.reply(f"Ошибка при обработке данных: {val_err}")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")
    await state.finish()

# Создание розыгрыша и его повторение
async def da(message: types.Message, admin_ids, user_id=None):
    # Получаем данные для розыгрыша
    user_data = repeat_data.get(user_id or message.from_user.id)
    if not user_data:
        await message.reply("Нет данных для создания розыгрыша.")
        return

    try:
        await asyncio.sleep(2)
        response = forum.threads.contests.money.create_by_time(
            post_body=user_data['body'], prize_data_money=user_data['price'],
            count_winners=1, length_value=user_data['dateX'], length_option=user_data['dateY'],
            require_like_count=1, require_total_like_count=50, secret_answer=secret,
            tags=user_data['tags'], title=user_data['title']
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
        await message.reply(f"Произошла ошибка: {e}")

# Планирование повторяющейся задачи
async def schedule_repeating_da(message: types.Message, admin_ids):
    user_id = message.from_user.id

    if user_id in tasks and not tasks[user_id].done():
        await message.reply("Задача уже выполняется!")
        return

    # Создаем новую повторяющуюся задачу
    task = asyncio.create_task(repeat_da_command(message, admin_ids))
    tasks[user_id] = task
    await message.reply(f"Команда будет повторяться каждые {interval_days} дня(ей).", reply_markup=get_main_keyboard())

# Отмена повторяющейся задачи
async def cancel_repeating_da(message: types.Message):
    user_id = message.from_user.id

    if user_id in tasks:
        task = tasks[user_id]
        if not task.done():
            task.cancel()  # Отменяем задачу
            await message.reply("Повторение команды успешно остановлено.")
        else:
            await message.reply("Задача уже завершена.")
    else:
        await message.reply("Нет активных задач для остановки.")

# Регистрация обработчиков
def register_repeat_handlers(dp: Dispatcher, admin_ids):
    dp.register_message_handler(lambda message, state: start_repeat_command(message, admin_ids), commands="repeat", state="*")
    dp.register_message_handler(lambda message, state: process_repeat_interval(message, admin_ids, state), state=RepeatForm.waiting_for_interval)
    dp.register_message_handler(lambda message: start_repeat_command(message, admin_ids), text="📄 Создавать розыгрыш каждые X дней")

    dp.register_message_handler(lambda message, state: get_link(message, state), state=Form.waiting_for_link)
    dp.register_message_handler(lambda message, state: get_other(message, state, admin_ids), state=Form.waiting_for_other)

    dp.register_message_handler(lambda message, state: da(message, admin_ids), text="Да, создавать")
    dp.register_message_handler(lambda message: cancel_repeating_da(message), commands="cancel")
