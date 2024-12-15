from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton, InlineKeyboardButton


def get_main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="📄 Создать новый розыгрыш"))
    keyboard.add(KeyboardButton(text="📄 Создавать розыгрыш каждые X дней"))
    keyboard.add(KeyboardButton(text="📄 Создать несколько розыгрышей"))
    return keyboard.as_markup(resize_keyboard=True)


def get_time_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="Да, создать"))
    keyboard.add(KeyboardButton(text="Нет"))
    return keyboard.as_markup(resize_keyboard=True)

def get_time1_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="Да, создавать"))
    keyboard.add(KeyboardButton(text="Отмена"))
    return keyboard.as_markup(resize_keyboard=True)



def inlinekey():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Одобрить", callback_data="approve_")
    keyboard.button(text="❌ Отмена", callback_data="reject_")
    return keyboard.as_markup()
