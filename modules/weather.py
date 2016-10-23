import os
import json
import arrow
import collections
import requests
import telegram
import jinja2
import pytz
import time

from leonard import Leonard
from modules.location import set_location

NAME = 'Weather'

WEATHER_MESSAGE = jinja2.Template("Right now - *{{ temperature }} ℉*, _{{ summary|lower }}_ "
                                  "{{ emoji }}\n\n{{ day_summary }}")
HOUR_FORECAST_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nYour hour weather forecast:\n\n{% for hour in hours %}"
                                        "{{ hour.time }} – *{{ hour.temperature }} ℉*, "
                                        "_{{ hour.summary|lower }}_ {{ hour.emoji }}\n{% endfor %}")
ENDPOINT_URL = 'https://api.darksky.net/forecast/{}'.format(os.environ['DARKSKY_TOKEN'])

OTHER_LOCATION_BUTTON = 'Send other location 📍'
HOUR_FORECAST_BUTTON = 'Hour forecast 🕘'

WEATHER_ICONS = {
    'rain': '☔',
    'clear-day': '☀️',
    'clear-night': '🌃',
    'snow': '❄️',
    'sleet': '🌨',
    'wind': '🍃',
    'fog': '🌁',
    'cloudy': '☁️',
    'partly-cloudy-day': '⛅',
    'partly-cloudy-night': '🌃',
}

SUBSCRIBES = collections.OrderedDict([
    ('Every morning', 'morning'),
    ('Every evening', 'evening'),
    ('Before rain', 'rain'),
])


def register(bot):
    bot.handlers['weather-show'] = show_weather
    bot.handlers['weather-change'] = change_weather
    bot.handlers['weather-morning'] = morning_forecast
    bot.handlers['weather-rain'] = morning_forecast

    bot.subscriptions.append(('{}:morning'.format(NAME), check_show_weather_morning, send_show_weather))
    bot.subscriptions.append(('{}:evening'.format(NAME), check_show_weather_evening, send_show_weather))
    # bot.subscriptions.append(('{}:rain'.format(NAME), check_show_weather_rain, send_show_weather))


def check_show_weather_morning(bot: Leonard):
    users = bot.redis.keys('user:*notifications:{}:{}'.format(NAME, 'morning'))
    return check_show_weather_condition(
        bot,
        lambda timezone: ('morning', arrow.now(timezone).datetime.hour in (8, 9, 10)),
        map(lambda x: x.decode('utf-8').split(':')[1], users) if users else []
    )


def check_show_weather_evening(bot: Leonard):
    users = bot.redis.keys('user:*notifications:{}:{}'.format(NAME, 'evening'))
    return check_show_weather_condition(
        bot,
        lambda timezone: ('evening', arrow.now(timezone).datetime.hour in (19, 20, 21)),
        map(lambda x: x.decode('utf-8').split(':')[1], users) if users else []
    )


def check_show_weather_condition(bot: Leonard, condition, users):
    result = []
    for u_id in users:
        user = eval(bot.redis.get('user:{}:location'.format(u_id)).decode('utf-8'))
        timezone = pytz.timezone(user['timezone'])
        name, correct = condition(timezone)
        if correct and int(time.time() * 1000) - \
                int(bot.user_get(u_id, 'notifications:{}:{}:last'.format(NAME, name)) or 0) > 86400000:
            result.append(int(u_id))
            bot.user_set(u_id, 'notifications:{}:{}:last'.format(NAME, name), int(time.time() * 1000))
    return result


# def check_show_weather_rain(bot):
#     result = []
#     for user in map(lambda x: x.decode('utf-8'), bot.redis.keys('user:*:location')):
#         u_id = user.split(':')[1]
#         user = send(bot.redis.get(user).decode('utf-8'))
#         timezone = pytz.timezone(user['timezone'])
#         time = datetime.datetime.now(timezone)
#         if time.hour == 10:
#             result.append(int(u_id))
#     return result


def send_show_weather(bot, users):
    if not users:
        return
    for user in users:
        show_weather(None, bot, user)


def show_weather(message, bot, u_id=None):
    if message:
        user_id = message.u_id
    else:
        user_id = u_id
    bot.user_set(user_id, 'next_handler', 'weather-change')
    bot.telegram.send_message(user_id, "Hold on, I'm loading weather information powered by Forecast.io ⌛",
                              reply_markup=telegram.ReplyKeyboardHide(), disable_web_page_preview=True)
    location = json.loads(bot.user_get(user_id, 'location'))
    text, reply_markup = build_basic_forecast(location, user_id, bot)
    bot.telegram.send_message(user_id, text,
                              reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)


def change_weather(message, bot):
    if message.location:
        set_location(bot, message.u_id, message.location)
        bot.call_handler(message, 'weather-show')
    elif message.text == HOUR_FORECAST_BUTTON:
        bot.call_handler(message, 'weather-hour')
        bot.call_handler(message, 'main-menu')
    else:
        bot.call_handler(message, 'main-menu')


def build_basic_forecast(location, user_id, bot):
    weather_data = get_weather(location['lat'], location['long'])
    bot.logger.info('Weather information: {}'.format(weather_data))
    bot.user_set(user_id, 'weather:data', json.dumps(weather_data))
    reply_markup = telegram.ReplyKeyboardMarkup(
        [[telegram.KeyboardButton(HOUR_FORECAST_BUTTON),
          telegram.KeyboardButton(OTHER_LOCATION_BUTTON, request_location=True)],
         [telegram.KeyboardButton(bot.MENU_BUTTON)]]
    )
    weather_message = WEATHER_MESSAGE.render(
        temperature=weather_data['currently']['temperature'],
        summary=weather_data['currently']['summary'],
        emoji=WEATHER_ICONS.get(weather_data['currently']['icon'], ''),
        day_summary=weather_data['hourly']['summary'],
        data=str(weather_data)[:100]
    )
    return weather_message, reply_markup


def morning_forecast(message, bot):
    weather_data = json.loads(bot.user_get(message.u_id, 'weather:data'))
    hours = []
    for i in range(0, min(16, len(weather_data['hourly']['data'])), 3):
        hour_weather = weather_data['hourly']['data'][i]
        hours.append({
            'time': arrow.get(hour_weather['time']).to(weather_data['timezone']).format('H:00'),
            'temperature': hour_weather['temperature'],
            'summary': hour_weather['summary'],
            'emoji': WEATHER_ICONS.get(hour_weather['icon'], '')
        })
    bot.telegram.send_message(message.u_id, HOUR_FORECAST_MESSAGE.render(hours=hours),
                              reply_markup=telegram.ReplyKeyboardHide(),
                              parse_mode=telegram.ParseMode.MARKDOWN)


def get_weather(lat, lng):
    response = requests.get(ENDPOINT_URL + '/{},{}'.format(lat, lng))
    return response.json()
