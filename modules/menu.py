import random
import telegram

MENU = [[('handler', 'Venues ☕', 'foursquare-location-choice'),
         ('handler', 'Weather 🌤', 'weather-show'),
         ('handler', 'News 📰', 'news-get-entry')],
        [('handler', 'Vinci 🌇', 'vinci-upload-image'),
         ('handler', 'Get Uber 🚘', 'uber-choose-location'),
         ('handler', 'Wolfram 📊', 'wolfram-ask')],
        [('handler', '9GAG 😅', 'meme-show'),
         ('handler', 'Product Hunt 😺', 'producthunt-get-entry'), ],
        [('handler', 'Wikipedia 📚', 'wiki-search'),
         ('handler', 'Subscriptions 📬', 'subscriptions-show')],
        [('handler', 'Change location 🗺', 'location-new')]]

GREETING_PHRASES = ['What do you want to do? 🤖',
                    'Do you need anything? 🤖',
                    'How can I help you today? 🤖',
                    'Any way I can help you? 🤖']


def register(bot):
    bot.handlers['main-menu'] = main_menu

    bot.callback_handlers['main-menu-callback'] = main_menu_callback


def main_menu(message, bot, phrase=None):
    if not bot.user_get(message.u_id, 'registered'):
        bot.call_handler(message, 'welcome-message')
        return

    if not message.moved:
        for line in MENU:
            for row in line:
                if row[0] == 'handler' and row[1] == message.text:
                    message.handler = row[2]
                    return bot.call_handler(message, row[2])

    keyboard = get_keyboard()
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    bot.telegram.send_message(message.u_id, phrase or random.choice(GREETING_PHRASES),
                              reply_markup=reply_markup)


def main_menu_callback(query, bot):
    query.message.moved = True
    bot.call_handler(query.message, 'main-menu')


def get_keyboard():
    keyboard = []
    for line in MENU:
        subkeyboard = []
        for row in line:
            if row[0] == 'handler':
                subkeyboard.append(row[1])
        if subkeyboard:
            keyboard.append(subkeyboard)
    return keyboard
