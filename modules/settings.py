from telegram import ReplyKeyboardMarkup, KeyboardButton
from modules.location import set_location

CHANGE_TEMP = 'Change Celsius/Fahrenheit'
CHANGE_LOCATION = 'Change location'


def register(bot):
    bot.handlers['settings-show'] = show_settings
    bot.handlers['settings-change'] = change_settings


def show_settings(message, bot):
    bot.telegram.send_message(
        message.u_id,
        'What do you want to change in my behaviour?',
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton(CHANGE_TEMP)],
            [KeyboardButton(CHANGE_LOCATION, request_location=True)],
            [bot.MENU_BUTTON]
        ])
    )
    bot.user_set(message.u_id, 'next_handler', 'settings-change')


def change_settings(message, bot):
    user_id = message.u_id
    if message.location:
        set_location(bot, user_id, message.location, True)
        bot.send_message(user_id, 'Your location has been changed, now you will get weather in your city')
    elif message.text == CHANGE_TEMP:
        was = bot.user_get(user_id, 'temperature', 'F')
        if was == 'F':
            bot.user_set(user_id, 'temperature', 'C')
            now = 'Celsius'
        else:
            bot.user_set(user_id, 'temperature', 'F')
            now = 'Fahrenheit'
        bot.send_message(user_id, 'Alright, all weather forecasts will be in ' + now)
    bot.call_handler(message, 'settings-show')
