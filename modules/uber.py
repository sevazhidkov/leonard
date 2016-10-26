import os
import telegram
from flask import request, redirect

OAUTH_START_INVITE_FIRST = "Oh, it looks like you didn't connected your Uber account 🤔"
OAUTH_START_INVITE_SECOND = ("Don't worry, it's easy and you should do it only once.\n"
                             "Just click button below and go through Uber authorization ✅")

CLIENT_ID = os.environ['UBER_CLIENT_ID']
CLIENT_SECRET = os.environ['UBER_CLIENT_SECRET']

AUTH_URL = "https://login.uber.com/oauth/v2/authorize?client_id={}&response_type=code"


def register(bot):
    global oauth_redirect
    bot.handlers['uber-choose-location'] = choose_location
    bot.handlers['uber-oauth-start'] = oauth_start

    oauth_redirect = bot.app.route('/uber/redirect')(oauth_redirect)


def choose_location(message, bot):
    if bot.user_get(message.u_id, 'uber:authorized') != '1':
        bot.call_handler(message, 'uber-oauth-start')
        return
    bot.telegram.send_message(message.u_id, 'Hello its me.')


def oauth_start(message, bot):
    keyboard = telegram.InlineKeyboardMarkup([
        [telegram.InlineKeyboardButton('Connect to Uber 🚘', url=AUTH_URL.format(CLIENT_ID))],
        [telegram.InlineKeyboardButton(bot.MENU_BUTTON, callback_data='main-menu-callback')]
    ])
    bot.send_message(message.u_id, OAUTH_START_INVITE_FIRST, reply_markup=telegram.ReplyKeyboardHide())
    bot.send_message(message.u_id, OAUTH_START_INVITE_SECOND, reply_markup=keyboard)


def oauth_redirect():
    print(request.params)
    return redirect('https://telegram.me/leonardbot')
