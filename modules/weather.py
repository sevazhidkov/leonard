import os
import json
import arrow
import collections
import requests
import telegram
import jinja2
import pytz
import datetime

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
    ('Every minute', (['interval'], {'minutes': 1}, 'minute')),
    ('Every hour', (['interval'], {'hours': 1}, 'hour')),
])


def register(bot):
    bot.handlers['weather-show'] = show_weather
    bot.handlers['weather-change'] = change_weather
    bot.handlers['weather-hour'] = hour_forecast

    bot.subscriptions.append(('{}:morning'.format(NAME), check_show_weather_morning, eval_show_weather))


def check_show_weather_morning(bot):
    result = []
    for user in map(lambda x: x.decode('utf-8'), bot.redis.keys('user:*:location')):
        u_id = user.split(':')[1]
        user = eval(bot.redis.get(user).decode('utf-8'))
        timezone = pytz.timezone(user['timezone'])
        time = datetime.datetime.now(timezone)
        if time.hour == 10:
            result.append(int(u_id))
    return result


def eval_show_weather(bot, users):
    pass


def show_weather(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'weather-change')
    bot.telegram.send_message(message.u_id, "Hold on, I'm loading weather information powered by Forecast.io ⌛",
                              reply_markup=telegram.ReplyKeyboardHide(), disable_web_page_preview=True)
    location = json.loads(bot.user_get(message.u_id, 'location'))
    text, reply_markup = build_basic_forecast(location, message, bot)
    bot.telegram.send_message(message.u_id, text,
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


def build_basic_forecast(location, message, bot):
    weather_data = get_weather(location['lat'], location['long'])
    bot.logger.info('Weather information: {}'.format(weather_data))
    bot.user_set(message.u_id, 'weather:data', json.dumps(weather_data))
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
    return (weather_message, reply_markup)


def hour_forecast(message, bot):
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
