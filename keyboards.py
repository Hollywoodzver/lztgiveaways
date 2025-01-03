from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton, InlineKeyboardButton


def get_main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="📄 Создать новый розыгрыш"))
    keyboard.add(KeyboardButton(text="📄 Создавать розыгрыш каждые X дней"))
    keyboard.add(KeyboardButton(text="📄 Создать несколько розыгрышей"))
    keyboard.add(KeyboardButton(text="📄 Создать из bb-code"))
    keyboard.add(KeyboardButton(text="❓ Последние розыгрыши"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

def inlinekey():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Одобрить", callback_data="approve_")
    keyboard.button(text="❌ Отмена", callback_data="reject_")
    return keyboard.as_markup()

def bbkey():
    keyboard = InlineKeyboardBuilder() 
    keyboard.button(text="✅ Одобрить", callback_data="bbapprove_")
    keyboard.button(text="❌ Отмена", callback_data="bbreject_")
    return keyboard.as_markup()

def cbtkey():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Одобрить", callback_data="cbtapprove_")
    keyboard.button(text="❌ Отмена", callback_data="cbtreject_")
    return keyboard.as_markup()

def masskey():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Одобрить", callback_data="massapprove_")
    keyboard.button(text="❌ Отмена", callback_data="massreject_")
    return keyboard.as_markup()
