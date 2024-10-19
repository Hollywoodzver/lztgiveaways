import re
from aiogram.fsm.context import FSMContext
import requests
from LOLZTEAM.API import Forum, Market
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
import asyncio
import config
from config import token, secret
from keyboards import get_main_keyboard, inlinekey
from aiogram.filters import StateFilter, CommandStart
import logging


logging.basicConfig(level=logging.INFO)

router=Router()
admin_ids=config.ADMIN_IDS


class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_second_text = State()  # Состояние для второго текста

market = Market(token=token, language="en")
forum = Forum(token=token, language="en")

@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_ids:
        await message.answer(f"Привет, админ!  Выберите действие:", reply_markup=get_main_keyboard())

@router.message(F.text == '📄 Создать новый розыгрыш')
async def give_command(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_ids:

        await message.reply("Отправьте ссылку на розыгрыш, содержание которого хотите скопировать:")
        logging.info(f"Received command: from user {message.from_user.id}")
        await state.set_state(Form.waiting_for_text)

@router.message(StateFilter(Form.waiting_for_text))
async def process_give(message: types.Message, state: FSMContext):
    logging.info(f"Process message in waiting_for_text state: {message.text}")

    first_input = message.text  # Сохраняем введенный текст в переменную
    pattern = re.search(r'threads/(\d+)', first_input)       
    if pattern:
        await state.update_data(first_input=first_input)
        first_input = message.text  # Сохраняем введенный текст в переменную
        await state.update_data(first_input=first_input)  # Сохраняем первый ввод
        await message.reply(f"Теперь введите сумму розыгрыша, срок розыгрыша, тип срока (minutes, hours, days)\n\nПример: 555, 2, hours (Будет создан розыгрыш на 555₽, Сроком 2 часа)")
        await state.set_state(Form.waiting_for_second_text) # Устанавливаем состояние для второго текста
    else:
        await message.reply(f"Похоже, вы ввели не ссылку. Попробуйте сначала")
        await state.clear()


@router.message(StateFilter(Form.waiting_for_second_text))
async def next_give(message: types.Message, state: FSMContext):
    global second_input, price, date, date2, first_input
    try:
        second_input = message.text  # Сохраняем введенный текст в переменную
        parts = [part.strip() for part in second_input.split(",")]
        price = parts[0]
        date = parts[-2]
        date2 = parts[-1]
        user_data = await state.get_data()  # Получаем данные о состоянии
        first_input = user_data.get('first_input')  # Получаем первый ввод

        await state.clear()  # Завершаем состояние
        if int(price)<500:
            await message.reply("Сумма розыгрыша не может быть меньше 500₽\nПопробуйте снова")
        elif date2 not in ('minutes', 'hours', 'days'):
            await message.reply("Тип даты должен быть одним из следующего: minutes, hours, days\nПопробуйте снова.")

        elif int(date)>3 and date2=='days':
            await message.reply('Срок розыгрша не может быть больше, чем 3 days.')
        else:
            
            await message.reply(
                f"Содержание розыгрыша: {first_input}\nprice: {price}₽\nСрок розыгрыша: {date} {date2}\nСоздавать розыгрыш?", reply_markup=inlinekey()
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
                global thread_tags
                title1 = response.json()['thread']['thread_title']
                body = response.json()['thread']['first_post']['post_body']
                response_data=response.json()
                thread_tags = response_data['thread']['thread_tags']

            # Если thread_tags это словарь, то преобразуем его в список
            if isinstance(thread_tags, dict):
                thread_tags = list(thread_tags.values())


            else:
            # Если нужных ключей нет, присваиваем пустой список
                thread_tags = []

    except Exception as e:
        await message.reply(f"Ответ сервера: {e}\nПопробуйте сначала")
        await state.clear()

@router.callback_query()
async def confirm_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    if action == "approve_":
        try:
            await asyncio.sleep(2)
            response = response = forum.threads.contests.money.create_by_time(post_body=body,prize_data_money=int(price), count_winners=1,
                                                                length_value=date, length_option=date2, require_like_count=1,
                                                                require_total_like_count=50, secret_answer=secret, tags=thread_tags, title=title1)
            
            thread_id = response.json()["thread"]["links"]["permalink"]
            print(f"Розыгрыш {thread_id} успешно создан!")
            await callback_query.message.edit_text(f"Розыгрыш успешно создан\n{thread_id}")
            if 'errors' in response.json():
                await callback_query.message.edit_text("Ошибки в ответе:", response.json()['errors'])
   
        except Exception as err:
            await callback_query.message.edit_text(f"Произошла непредвиденная ошибка: {err}")
            

    if action == "reject_":
        await callback_query.message.edit_text(f"Заявка отклонена.")
