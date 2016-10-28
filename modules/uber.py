import os
import requests
import telegram
from flask import request, redirect

from libs.shrt import short_user_link
from libs.utils import build_bot, FakeMessage

OAUTH_START_INVITE_FIRST = "Oh, it looks like you didn't connected your Uber account 🤔"
OAUTH_START_INVITE_SECOND = ("Don't worry, it's easy and you should do it only once.\n"
                             "Just click button below and go through Uber authorization ✅")
CHOOSE_CURRENT_LOCATION = "OK, please tell me your location – start point for your route 🗺"
CHOOSE_YOUR_DESTINATION = "Thanks! So where do you want to go? 🗺"

HOME_BUTTON =
WORK_BUTTON = 

CLIENT_ID = os.environ['UBER_CLIENT_ID']
CLIENT_SECRET = os.environ['UBER_CLIENT_SECRET']
REDIRECT_URL = os.environ['UBER_REDIRECT_URL']

AUTH_URL = "https://login.uber.com/oauth/v2/authorize?client_id={}&response_type=code"
TOKEN_URL = "https://login.uber.com/oauth/v2/token"
PLACES_URL = "https://api.uber.com/v1/places/{}"


def register(bot):
    global oauth_redirect
    bot.handlers['uber-choose-location'] = choose_current_location
    bot.handlers['uber-choose-destination'] = choose_destination
    bot.handlers['uber-oauth-start'] = oauth_start

    oauth_redirect = bot.app.route('/uber/redirect')(oauth_redirect)


def choose_current_location(message, bot):
    if bot.user_get(message.u_id, 'uber:authorized') != '1':
        bot.call_handler(message, 'uber-oauth-start')
        return
    bot.user_set(message.u_id, 'next_handler', 'uber-choose-destination')
    bot.telegram.sendChatAction(message.u_id, 'typing')

    token = bot.user_get(message.u_id, 'uber:access_token')
    if not token:
        token = refresh_token(bot, message.u_id)

    place_buttons = []
    for place_id, place_button in [['home', '🏠 Home'], ['work', '👔 Work']]:
        response = requests.get(PLACES_URL.format(place_id), headers={
            'Authorization': 'Bearer {}'.format(token)
        }).json()
        print(response)
        if 'address' in response:
            bot.user_set(message.u_id, 'uber:places:{}'.format(place_id), '1')
            place_buttons.append(place_button)
    keyboard = telegram.ReplyKeyboardMarkup([
        [telegram.KeyboardButton("📍 Send location", request_location=True)],
        place_buttons,
        [bot.MENU_BUTTON],
    ])
    bot.telegram.send_message(message.u_id, CHOOSE_CURRENT_LOCATION, reply_markup=keyboard)


def choose_destination(message, bot):
    bot.telegram.send_message(message.u_id, CHOOSE_YOUR_DESTINATION)


def oauth_start(message, bot):
    keyboard = telegram.InlineKeyboardMarkup([
        [telegram.InlineKeyboardButton(
            'Connect to Uber 🚘',
            url=short_user_link(message.u_id, AUTH_URL.format(CLIENT_ID))
        )],
        [telegram.InlineKeyboardButton(bot.MENU_BUTTON, callback_data='main-menu-callback')]
    ])
    bot.send_message(message.u_id, OAUTH_START_INVITE_FIRST, reply_markup=telegram.ReplyKeyboardHide())
    bot.send_message(message.u_id, OAUTH_START_INVITE_SECOND, reply_markup=keyboard)


def oauth_redirect():
    code = request.args.get('code')
    access_data = requests.post(TOKEN_URL, data={
        'client_secret': CLIENT_SECRET,
        'client_id': CLIENT_ID,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URL,
        'code': code
    }).json()
    print(access_data)
    print(request.cookies)

    bot = build_bot()
    u_id = int(bot.redis.get('core:shrt:hash:{}'.format(request.cookies['user'])))
    bot.user_set(u_id, 'uber:access_token', access_data['access_token'], ex=access_data['expires_in'])
    bot.user_set(u_id, 'uber:refresh_token', access_data['refresh_token'])
    bot.user_set(u_id, 'uber:authorized', '1')

    fake_message = FakeMessage()
    fake_message.u_id = u_id
    bot.call_handler(fake_message, 'uber-choose-location')

    return redirect('https://telegram.me/leonardbot')


def refresh_token(bot, u_id):
    response = requests.post(TOKEN_URL, {
        'client_secret': CLIENT_SECRET,
        'client_id': CLIENT_ID,
        'grant_type': 'refresh_token',
        'redirect_uri': REDIRECT_URL,
        'refresh_token': bot.redis.user_get(u_id, 'uber:refresh_token')
    })
    bot.user_set(u_id, 'uber:access_token', access_data['access_token'], ex=access_data['expires_in'])
    bot.user_set(u_id, 'uber:refresh_token', access_data['refresh_token'])
    return access_data['access_token']
