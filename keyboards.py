from aiogram import types

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["📄 Создать новый розыгрыш", "📄 Создавать розыгрыш каждые X дней"] 
    keyboard.add(buttons[0])
    keyboard.add(buttons[1])
    return keyboard

def get_time_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Да, создавать", "Нет"] 
    keyboard.add(buttons[0], buttons[1])
    return keyboard
