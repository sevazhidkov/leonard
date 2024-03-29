import os
import json
import telegram
from mapbox import Geocoder

from libs.googleapis import get_timezone

WELCOME_LOCATION_SETUP = ("I have a lot of amazing functions that depends on your location 🌍, " +
                          "can you tell it?")

HOW_TO_SEND_LOCATION = ("You can attach location to message 📎 or type name of your city 🔡")
TYPE_LOCATION_AGAIN = "Oh, sorry, I don't understand 🙁\n\nYou can try again 🔡 or send me a location 🌐"

geocoder = Geocoder()


def register(bot):
    bot.handlers['welcome-location-setup'] = welcome_location_setup
    bot.handlers['location-setup-result'] = location_setup_result
    bot.handlers['new-location-setup-result'] = new_location_setup_result
    bot.handlers['location-new'] = new_location


def geocode(location_name, bot=None):
    response = geocoder.forward(location_name).json()
    if bot:
        bot.logger.info('Mapbox response: {}'.format(response))
    if 'features' not in response or not response['features']:
        return None
    place = response['features'][0]
    country = None
    for context in place['context']:
        if context['id'].startswith('country'):
            country = context['short_code']
    return {
        'long': place['center'][0],
        'lat': place['center'][1],
        'full_name': place.get('place_name'),
        'name': place.get('text'),
        'country': country,
        'timezone': get_timezone(place['center'][1], place['center'][0])
    }


def reverse_geocode(lat, long, bot=None):
    response = geocoder.reverse(long, lat).json()
    if bot:
        bot.logger.info('Mapbox response: {}'.format(response))
    if len(response['features']) == 0:
        return None
    place = response['features'][0]
    country = None
    for context in place['context']:
        if context['id'].startswith('country'):
            country = context['short_code']
    return {
        'long': place['center'][0],
        'lat': place['center'][1],
        'full_name': place.get('place_name'),
        'name': place.get('text'),
        'country': country,
        'timezone': get_timezone(place['center'][1], place['center'][0])
    }


def welcome_location_setup(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'location-setup-result')
    bot.telegram.send_message(
        message.u_id, WELCOME_LOCATION_SETUP,
        reply_markup=telegram.ReplyKeyboardMarkup(
            [[telegram.KeyboardButton('📍 Send current location', request_location=True)]],
            resize_keyboard=True
        )
    )
    bot.telegram.send_message(message.u_id, HOW_TO_SEND_LOCATION)


def location_setup_result(message, bot):
    if not message.location:
        result = geocode(message.text, bot)
        if not result:
            bot.telegram.send_message(message.u_id, TYPE_LOCATION_AGAIN)
            bot.user_set(message.u_id, 'next_handler', 'location-setup-result')
            return
        bot.user_set(message.u_id, 'location', json.dumps(result))
    else:
        set_location(bot, message.u_id, message.location)
    bot.call_handler(message, 'welcome-setup-result')


def set_location(bot, u_id, location):
    result = reverse_geocode(location['latitude'], location['longitude'], bot)
    if result:
        bot.user_set(u_id, 'location', json.dumps(result))
        return result


def new_location(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'new-location-setup-result')
    bot.telegram.send_message(message.u_id, HOW_TO_SEND_LOCATION, reply_markup=telegram.ReplyKeyboardMarkup(
        [
            [telegram.KeyboardButton('📍 Send current location', request_location=True)],
            [bot.MENU_BUTTON]
        ],
        resize_keyboard=True
    ))


def new_location_setup_result(message, bot):
    if not message.location:
        result = geocode(message.text, bot)
        if not result:
            bot.telegram.send_message(message.u_id, TYPE_LOCATION_AGAIN)
            bot.user_set(message.u_id, 'next_handler', 'new-location-setup-result')
            return
        bot.user_set(message.u_id, 'location', json.dumps(result))
    else:
        set_location(bot, message.u_id, message.location)
    bot.telegram.send_message(message.u_id, 'Thanks 👌')
    bot.call_handler(message, 'main-menu')
