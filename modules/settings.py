from telegram import ReplyKeyboardMarkup, KeyboardButton
from modules.location import set_location

CHANGE_LOCATION = 'Change location'


def register(bot):
    bot.handlers['settings-show'] = show_settings
    bot.handlers['settings-change'] = change_settings


def show_settings(message, bot):
    bot.telegram.send_message(
        message.u_id,
        'Hm... What do you want to change?',
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton(CHANGE_LOCATION, request_location=True)],
            [bot.MENU_BUTTON]
        ])
    )
    bot.user_set(message.u_id, 'next_handler', 'settings-change')


def change_settings(message, bot):
    user_id = message.u_id
    if message.location:
        set_location(bot, user_id, message.location)
        bot.send_message(user_id, 'Your location has been changed, now you will get weather in your current city')
    bot.call_handler(message, 'main-menu')
