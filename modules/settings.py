from telegram import ReplyKeyboardMarkup, KeyboardButton


def register(bot):
    bot.handlers['settings-show'] = show_settings
    # bot.handlers['temperature-change'] = change_temperature
    # bot.handlers['timezone-change'] = change_timezone


def show_settings(message, bot):
    bot.telegram.send_message(
        message.u_id,
        'What do you want to change in my behaviour?',
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton('Change Celsius/Fahrenheit')]
        ])
    )
