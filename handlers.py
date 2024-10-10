from aiogram import Dispatcher, types, Bot
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
from LOLZTEAM.API import Forum, Market

import requests

class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_second_text = State()  # Состояние для второго текста



token = "Your Forum Token"
secret = "your secret answer"

market = Market(token=token, language="en")
forum = Forum(token=token, language="en")

async def start(message: types.Message, admin_ids):
    if message.from_user.id in admin_ids:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["📄 Создать новый розыгрыш"] 
        keyboard.add(buttons[0])
        await message.reply(f"Привет, админ!  Выберите действие:", reply_markup=keyboard)

async def give_command(message: types.Message, admin_ids):
    if message.from_user.id in admin_ids:
        await message.reply("Отправьте ссылку на розыгрыш, содержание которого хотите скопировать:")
        await Form.waiting_for_text.set() 

async def process_give(message: types.Message, state: FSMContext):
    first_input = message.text  # Сохраняем введенный текст в переменную
    await state.update_data(first_input=first_input)  # Сохраняем первый ввод
    await message.reply(f"Теперь введите сумму розыгрыша, срок розыгрыша, тип срока (minutes, hours, days)\n\nПример: 555, 2, hours (Будет создан розыгрыш на 555₽, Сроком 2 часа)")
    await Form.waiting_for_second_text.set()  # Устанавливаем состояние для второго текста


async def next_give(message: types.Message, state: FSMContext):
    global second_input, price, date, date2, first_input
    second_input = message.text  # Сохраняем введенный текст в переменную
    price = second_input.split(", ")[0]
    date = second_input.split(", ")[-2]
    date2 = second_input.split(", ")[-1]
    user_data = await state.get_data()  # Получаем данные о состоянии
    first_input = user_data.get('first_input')  # Получаем первый ввод

    await state.finish()  # Завершаем состояние
    
    keyboard = InlineKeyboardMarkup()
    approve_button = InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_")
    reject_button = InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_")
    keyboard.add(approve_button, reject_button)
    await message.reply(
        f"Содержание розыгрыша: {first_input}\nprice: {price}₽\nСрок розыгрыша: {date} {date2}\nСоздавать розыгрыш?", reply_markup=keyboard
        )

    matc = re.search(r'threads/(\d+)', first_input)
    if matc:
        thread_i = matc.group(1)
        print(f"Forum response data: {thread_i}")  # Отладочный вывод
        url = f"https://api.zelenka.guru/threads/{thread_i}"

        headers = {"accept": "application/json",
                   "authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        global title1, body
        title1 = response.json()['thread']['thread_title']
        body = response.json()['thread']['first_post']['post_body']


async def confirm_callback(callback_query: types.CallbackQuery, admin_ids):
    action = callback_query.data
    if action == "approve_":
        try:
            response = forum.threads.contests.money.create_by_time(post_body=body,prize_data_money=int(price), count_winners=1,
                                                                length_value=date, length_option=date2, require_like_count=1,
                                                                require_total_like_count=50, secret_answer=secret, title=title1)
            print(response.json())
            thread_id = response.json()["thread"]["links"]["permalink"]
            await callback_query.message.edit_text(f"Розыгрыш успешно создан\n{thread_id}")
            if 'errors' in response.json():
                await callback_query.message.edit_text("Ошибки в ответе:", response.json()['errors'])
        except NameError as e:
             await callback_query.message.edit_text(f"Убедитесь, что {first_input} - ссылка на тему")
        except requests.exceptions.HTTPError as http_err:
            await callback_query.message.edit_text(f"HTTP ошибка: {http_err}")
        except requests.exceptions.RequestException as req_err:
            await callback_query.message.edit_text(f"Ошибка запроса: {req_err}")
        except Exception as err:
            await callback_query.message.edit_text(f"Произошла непредвиденная ошибка: {err}")
        except ValueError as e:
             await callback_query.message.edit_text(f"Сумма розыгрыша должна быть числом. Также убедитесь, что срок розыгрыша не более 3-х дней")
        
    if action == "reject_":
        await callback_query.message.edit_text(f"Заявка отклонена.")





def register_handlers(dp: Dispatcher, admin_ids):
    dp.register_message_handler(lambda message, state: process_give(message, state), state=Form.waiting_for_text)
    dp.register_message_handler(lambda message, state: next_give(message, state), state=Form.waiting_for_second_text)
    dp.register_message_handler(lambda message: start(message, admin_ids), commands="start", state="*")
    dp.register_message_handler(lambda message: give_command(message, admin_ids),
                                text="📄 Создать новый розыгрыш")
    dp.register_callback_query_handler(lambda callback_query: confirm_callback(callback_query, admin_ids),
                                       lambda c: c.data.startswith(('approve_', 'reject_')))
