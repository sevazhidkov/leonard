import os
import json
import jinja2
import requests
import telegram
from flask import request, redirect

from libs.shrt import short_user_link
from libs.utils import build_bot, FakeMessage

from modules.location import set_location

OAUTH_START_INVITE_FIRST = "Oh, it looks like you didn't connected your Uber account 🤔"
OAUTH_START_INVITE_SECOND = ("Don't worry, it's easy and you should do it only once.\n"
                             "Just click button below and go through Uber authorization ✅")
CHOOSE_CURRENT_LOCATION = "OK, please tell me your location – start point for your route 🗺"
CHOOSE_YOUR_DESTINATION = "Thanks! So where do you want to go? 🗺\n\nSend location of your destination 📍 or choose a saved place 🚗"
CHOOSE_PRODUCT = jinja2.Template("Cool 👌 Everything is ready to get a Uber - you just "
                                 "need to choose suitable Uber product and car'll be on its way 🚘\n\n"
                                 "{% for product in products %}*{{ product.display_name }}* – "
                                 "{{ product.description }}\n{% endfor %}")
ORDERING_CAR = "Good choice! Wait a second, I'm ordering car for you 🕐"
ORDER_ERROR = "Unfortunally I can't process this order 😒\n\nMy developer notified, please try again later 🕘"
ORDER_CARD = jinja2.Template("*Uber order 🚘*\n\n"
                             "_Your order has been sent to Uber. I will send you "
                             "all updates._")

HOME_BUTTON = '🏡 Home'
WORK_BUTTON = '👔 Work'

CLIENT_ID = os.environ['UBER_CLIENT_ID']
CLIENT_SECRET = os.environ['UBER_CLIENT_SECRET']
REDIRECT_URL = os.environ['UBER_REDIRECT_URL']

AUTH_URL = "https://login.uber.com/oauth/v2/authorize?client_id={}&response_type=code&scope=profile places ride_widgets request"
TOKEN_URL = "https://login.uber.com/oauth/v2/token"
PLACES_URL = "https://sandbox-api.uber.com/v1/places/{}"
PRODUCTS_URL = "https://sandbox-api.uber.com/v1/products"
ORDER_URL = "https://sandbox-api.uber.com/v1/requests"
CURRENT_ORDER_URL = "https://sandbox-api.uber.com/v1/requests/current"

PLACE_IDS = {HOME_BUTTON: 'home', WORK_BUTTON: 'work'}



def register(bot):
    global oauth_redirect
    bot.handlers['uber-oauth-start'] = oauth_start
    bot.handlers['uber-choose-location'] = choose_current_location
    bot.handlers['uber-choose-destination'] = choose_destination
    bot.handlers['uber-choose-product'] = choose_product
    bot.handlers['uber-confirm-order'] = confirm_order

    bot.callback_handlers['uber-cancel-order'] = cancel_order

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
    for place_id, place_button in [['home', HOME_BUTTON], ['work', WORK_BUTTON]]:
        if bot.user_get(message.u_id, 'uber:places:{}'.format(place_id)):
            place_buttons.append(place_button)
            continue
        response = requests.get(PLACES_URL.format(place_id), headers={
            'Authorization': 'Bearer {}'.format(token)
        }).json()
        if 'address' in response:
            bot.user_set(message.u_id, 'uber:places:{}'.format(place_id), '1', ex=60 * 60 * 24 * 14)
            place_buttons.append(place_button)
    base_location_name = json.loads(bot.user_get(message.u_id, 'location'))['full_name']
    keyboard = telegram.ReplyKeyboardMarkup([
        [telegram.KeyboardButton("📍 Current location", request_location=True)],
        place_buttons,
        ['📦 {}'.format(base_location_name)],
        [bot.MENU_BUTTON],
    ])
    bot.telegram.send_message(message.u_id, CHOOSE_CURRENT_LOCATION, reply_markup=keyboard)

    bot.user_set(message.u_id, 'uber:location:place_id', '')
    bot.user_set(message.u_id, 'uber:destination:location', '')
    bot.user_set(message.u_id, 'uber:destination:place_id', '')


def choose_destination(message, bot):
    if (not message.location and
            (message.text not in [HOME_BUTTON, WORK_BUTTON] and '📦' not in message.text)):
        bot.call_handler(message, 'uber-choose-location')
        return
    bot.user_set(message.u_id, 'next_handler', 'uber-choose-product')
    keyboard = [[HOME_BUTTON, WORK_BUTTON],
                [bot.MENU_BUTTON]]
    if message.location:
        set_location(bot, message.u_id, message.location)
    elif message.text in [HOME_BUTTON, WORK_BUTTON]:
        bot.user_set(message.u_id, 'uber:location:place_id',
                     PLACE_IDS[message.text])
        keyboard[0].remove(message.text)

    bot.telegram.send_message(message.u_id, CHOOSE_YOUR_DESTINATION,
                              reply_markup=telegram.ReplyKeyboardMarkup(keyboard))


def choose_product(message, bot):
    if not message.location and message.text not in [HOME_BUTTON, WORK_BUTTON]:
        bot.call_handler(message, 'uber-choose-destination')
        return
    bot.user_set(message.u_id, 'next_handler', 'uber-confirm-order')

    if message.location:
        bot.user_set(message.u_id, 'uber:destination:location', json.dumps(message.location))
    else:
        bot.user_set(message.u_id, 'uber:destination:place_id', PLACE_IDS[message.text])

    # Prepare request to Uber - we'll add product id later
    request_data = {}
    user_location = json.loads(bot.user_get(message.u_id, 'location'))
    place_id = bot.user_get(message.u_id, 'uber:location:place_id')

    if place_id:
        request_data['start_place_id'] = place_id
    else:
        request_data['start_latitude'] = user_location['lat']
        request_data['start_longitude'] = user_location['long']

    place_id = bot.user_get(message.u_id, 'uber:destination:place_id')
    if place_id:
        request_data['end_place_id'] = place_id
    else:
        location = json.loads(bot.user_get(message.u_id, 'uber:destination:location'))
        request_data['end_latitude'] = location['latitude']
        request_data['end_longitude'] = location['longitude']

    bot.user_set(message.u_id, 'uber:request_data', json.dumps(request_data))

    token = bot.user_get(message.u_id, 'uber:access_token')
    products = requests.get(PRODUCTS_URL, headers={
        'Authorization': 'Bearer {}'.format(token)
    }, params={
        'latitude': user_location['lat'],
        'longitude': user_location['long'],
    }).json()

    product_ids = {}
    keyboard = [[bot.MENU_BUTTON]]
    products_per_row = 3
    current_row = []
    for product in products['products']:
        product_ids[product['display_name']] = product['product_id']
        if len(current_row) == products_per_row:
            keyboard.append(current_row)
            current_row = []
        current_row.append(product['display_name'])
    if current_row:
        keyboard.append(current_row)

    bot.telegram.send_message(message.u_id, CHOOSE_PRODUCT.render(products=products['products']),
                              parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=telegram.ReplyKeyboardMarkup(keyboard))
    bot.user_set(message.u_id, 'uber:avaliable_products', json.dumps(product_ids))


def confirm_order(message, bot):
    product_ids = json.loads(bot.user_get(message.u_id, 'uber:avaliable_products'))
    if message.text not in product_ids:
        bot.call_handler(message, 'uber-choose-product')
        return

    bot.send_message(message.u_id, ORDERING_CAR,
                     reply_markup=telegram.ReplyKeyboardHide())
    request_data = json.loads(bot.user_get(message.u_id, 'uber:request_data'))
    token = bot.user_get(message.u_id, 'uber:access_token')
    request_data['product_id'] = product_ids[message.text]
    response = requests.post(ORDER_URL, headers={
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json',
    }, data=json.dumps(request_data)).json()
    print(response)
    if 'errors' in response:
        bot.send_message(message.u_id, ORDER_ERROR)
        bot.call_handler(message, 'main-menu')
        return

    bot.user_set(message.u_id, 'uber:request_id', response['request_id'])
    bot.send_message(message.u_id, ORDER_CARD.render(data=response),
                     reply_markup=make_order_keyboard(bot, message.u_id, response),
                     parse_mode=telegram.ParseMode.MARKDOWN)


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

    bot = build_bot()
    u_id = int(bot.redis.get('core:shrt:hash:{}'.format(request.cookies['user'])))
    bot.user_set(u_id, 'uber:access_token', access_data['access_token'], ex=access_data['expires_in'])
    bot.user_set(u_id, 'uber:refresh_token', access_data['refresh_token'])
    bot.user_set(u_id, 'uber:authorized', '1')
    for place_id in ['home', 'work']:
        response = requests.get(PLACES_URL.format(place_id), headers={
            'Authorization': 'Bearer {}'.format(access_data['access_token'])
        }).json()
        if 'address' in response:
            bot.user_set(u_id, 'uber:places:{}'.format(place_id), '1', ex=60 * 60 * 24 * 14)

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


def cancel_order(query, bot):
    token = bot.user_get(query.u_id, 'uber:access_token')
    response = requests.delete(CURRENT_ORDER_URL, headers={
        'Authorization': 'Bearer {}'.format(token),
        'Content-Type': 'application/json',
    })
    bot.telegram.editMessageReplyMarkup(
        reply_markup=telegram.InlineKeyboardMarkup([]),
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    bot.send_message(query.u_id, 'Your order has been cancelled 🚫')
    bot.call_handler(query.message, 'main-menu')


def make_order_keyboard(bot, u_id, data):
    if 'errors' in data:
        return telegram.InlineKeyboardMarkup([])
    if data['status'] == 'processing':
        return telegram.InlineKeyboardMarkup(
            [[telegram.InlineKeyboardButton('Cancel order ❌', callback_data='uber-cancel-order')]]
        )