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

from libs.analytics import Tracker
from modules.location import set_location

NAME = 'Weather'
ORDER = 1

WEATHER_MESSAGE = jinja2.Template("Right now - *{{ temperature }} ℉*, _{{ summary|lower }}_ "
                                  "{{ emoji }}\n\n{{ day_summary }}")
FORECAST_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nYour {{ name }} weather forecast:\n\n{% for hour in hours %}"
                                   "{{ hour.time }} – *{{ hour.temperature }} ℉*, "
                                   "_{{ hour.summary|lower }}_ {{ hour.emoji }}\n{% endfor %}")

SUMMARY_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nYour {{ name }} weather forecast:\n\n"
                                  "_{{ summary }}_ {{ emoji }}\n"
                                  "_Wind speed_ - *{{ wind_speed }} MPH*\n"
                                  "_Temperature_ - *{{ temperature_min }} ℉ - {{ temperature_max }} ℉*\n")

RAIN_SOON = jinja2.Template("☔ ☔ ☔\nThere will be rain soon:\n\n{% for hour in hours %}"
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
    ('Weather forecast every morning 🌇', [
        'morning-forecast',
        ('Well, now every morning I will send weather forecasts specially for you ☺️', 'No more morning forecasts, honey.'),
        (8, 9, 10, 11)
    ]),
    ('Tomorrow forecast every evening 🌃', [
        'evening-forecast',
        ('Now you will get evening forecast!', 'Ok, if you want, I will stop sending you evening forecasts.'),
        (19, 20, 21, 22)
    ]),
    ('Notification and forecast an hour before rain ☔️', [
        'rain-forecast',
        ('Now you will get notification every time before rain!', 'Unfortunately, now you will be wet.'),
    ]),
])


def register(bot):
    bot.handlers['weather-show'] = show_weather
    bot.handlers['weather-change'] = change_weather
    bot.handlers['weather-hour'] = hour_forecast

    bot.subscriptions.append(('{}:morning-forecast'.format(NAME), check_show_weather_morning, send_show_forecast))
    bot.subscriptions.append(
        ('{}:evening-forecast'.format(NAME), check_show_weather_evening, send_show_forecast_evening))
    bot.subscriptions.append(('{}:rain-forecast'.format(NAME), check_send_notification_rain, send_notification_rain))


def check_show_weather_morning(bot: Leonard):
    users = bot.redis.keys('user:*:notifications:{}:{}'.format(NAME, 'morning-forecast'))
    return check_show_weather_condition(
        bot,
        list(SUBSCRIBES.values())[0][0],
        lambda timezone, u_id=None: arrow.now(timezone).datetime.hour in list(SUBSCRIBES.values())[0][2],
        users
    )


def check_show_weather_evening(bot: Leonard):
    users = bot.redis.keys('user:*:notifications:{}:{}'.format(NAME, 'evening-forecast'))
    return check_show_weather_condition(
        bot,
        list(SUBSCRIBES.values())[1][0],
        lambda timezone, u_id=None: arrow.now(timezone).datetime.hour in list(SUBSCRIBES.values())[1][2],
        users
    )


def check_send_notification_rain(bot: Leonard):
    return check_send_notification_weather(bot, list(SUBSCRIBES.values())[2][0])


def check_send_notification_weather(bot: Leonard, weather):
    users = bot.redis.keys('user:*:notifications:{}:{}'.format(NAME, weather))
    users = map(lambda x: x.decode('utf-8').split(':')[1], users) if users else []
    result = []

    def condition(location, uid=None):
        data = bot.user_get(uid, 'weather:data')
        if not data or time.time() - int(json.loads(data)['currently']['time']) > 3600:
            build_basic_forecast(location, uid, bot)
            weather_data = json.loads(bot.user_get(uid, 'weather:data'))
        else:
            weather_data = json.loads(data)
        return any([weather.rstrip('-forecast') in x['summary'].lower() for x in weather_data['hourly']['data'][1:24]])

    for u_id in users:
        user_location = bot.user_get(u_id, 'location')
        if not user_location:
            continue
        if condition(json.loads(user_location), u_id) and (
                    bot.redis.ttl('user:{}:notifications:{}:{}:last'.format(u_id, NAME, weather)) or 0
        ) <= 0:
            result.append(u_id)
            bot.redis.setex('user:{}:notifications:{}:{}:last'.format(u_id, NAME, weather), 1, 24 * 60 * 60)
    return result


def check_show_weather_condition(bot: Leonard, name, condition, users, expire=24 * 30 * 60):
    users = map(lambda x: x.decode('utf-8').split(':')[1], users) if users else []
    result = []
    for u_id in users:
        location = bot.user_get(u_id, 'location')
        if not location:
            timezone = pytz.timezone('UTC')
        else:
            user = json.loads(location)
            timezone = pytz.timezone(user['timezone'])
        if condition(timezone) and (
                    bot.redis.ttl('user:{}:notifications:{}:{}:last'.format(u_id, NAME, name)) or 0
        ) <= 0:
            result.append([int(u_id), arrow.now(timezone).datetime.hour])
            bot.redis.setex('user:{}:notifications:{}:{}:last'.format(u_id, NAME, name), 1, expire)
    return result, name


def send_notification_rain(bot, users):
    for u_id in users:
        hour_forecast(None, bot, None, RAIN_SOON, u_id, 'rain')


def show_weather(message, bot, u_id=None, subscription=False):
    if message:
        user_id = message.u_id
    else:
        user_id = u_id
    tracker = Tracker('weather', u_id=user_id)
    if not subscription:
        bot.user_set(user_id, 'next_handler', 'weather-change')
    location = json.loads(bot.user_get(user_id, 'location'))
    text, reply_markup = build_basic_forecast(location, user_id, bot)
    if subscription:
        reply_markup = None
    bot.telegram.send_message(user_id, text,
                              reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)

    if subscription:
        tracker.event('weather-subscription')
    else:
        tracker.event('weather-summary')

    return tracker


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


def send_show_forecast_evening(bot, args):
    for u_id, u_hour in args[0]:
        data = bot.user_get(u_id, 'weather:data')
        if not data or time.time() - int(json.loads(data)['currently']['time']) > 1800:
            location = json.loads(bot.user_get(u_id, 'location'))
            build_basic_forecast(location, u_id, bot)
            weather_data = json.loads(bot.user_get(u_id, 'weather:data'))
        else:
            weather_data = json.loads(data)
        hours = []
        for i in range(0, min(25 - u_hour, len(weather_data['hourly']['data']))):
            hour_weather = weather_data['hourly']['data'][i]
            hours.append({
                'time': arrow.get(hour_weather['time']).to(weather_data['timezone']).format('H:00'),
                'temperature': hour_weather['temperature'],
                'summary': hour_weather['summary'],
                'emoji': WEATHER_ICONS.get(hour_weather['icon'], '')
            })
        text = FORECAST_MESSAGE.render(name=args[1].rstrip('-forecast'), hours=hours)
        tomorrow = weather_data['daily']['data'][1]
        text += '\n\n' + SUMMARY_MESSAGE.render(
            name='tomorrow',
            summary=tomorrow['summary'],
            wind_speed=tomorrow['windSpeed'],
            emoji=WEATHER_ICONS.get(tomorrow['icon'], ''),
            temperature_min=tomorrow['temperatureMin'],
            temperature_max=tomorrow['temperatureMax']
        )

        bot.telegram.send_message(u_id, text, parse_mode=telegram.ParseMode.MARKDOWN)


def send_show_forecast(bot, args):
    for u_id, _ in args[0]:
        data = bot.user_get(u_id, 'weather:data')
        if not data or time.time() - int(json.loads(data)['currently']['time']) > 1800:
            location = json.loads(bot.user_get(u_id, 'location'))
            build_basic_forecast(location, u_id, bot)
            weather_data = json.loads(bot.user_get(u_id, 'weather:data'))
        else:
            weather_data = json.loads(data)
        hours = []
        for i in range(0, min(16, len(weather_data['hourly']['data'])), 3):
            hour_weather = weather_data['hourly']['data'][i]
            hours.append({
                'time': arrow.get(hour_weather['time']).to(weather_data['timezone']).format('H:00'),
                'temperature': hour_weather['temperature'],
                'summary': hour_weather['summary'],
                'emoji': WEATHER_ICONS.get(hour_weather['icon'], '')
            })
        bot.telegram.send_message(u_id, FORECAST_MESSAGE.render(name=args[1].rstrip('-forecast'), hours=hours),
                                  parse_mode=telegram.ParseMode.MARKDOWN)


def hour_forecast(message, bot, name=None, to_render=FORECAST_MESSAGE, u_id=None, only=None):
    if message:
        user_id = message.u_id
    else:
        user_id = u_id
    weather_data = json.loads(bot.user_get(user_id, 'weather:data'))
    hours = []
    if only:
        r = range(0, min(24, len(weather_data['hourly']['data'])))
    else:
        r = range(0, min(16, len(weather_data['hourly']['data'])), 3)
    for i in r:
        hour_weather = weather_data['hourly']['data'][i]
        hours.append({
            'time': arrow.get(hour_weather['time']).to(weather_data['timezone']).format('H:00'),
            'temperature': hour_weather['temperature'],
            'summary': hour_weather['summary'],
            'emoji': WEATHER_ICONS.get(hour_weather['icon'], '')
        })
    if only:
        hours = [x for x in hours[1:] if only in x['summary'].lower()]
    reply_markup = None if only else telegram.ReplyKeyboardHide()
    bot.telegram.send_message(user_id, to_render.render(name=name, hours=hours),
                              reply_markup=reply_markup,
                              parse_mode=telegram.ParseMode.MARKDOWN)


def get_weather(lat, lng):
    response = requests.get(ENDPOINT_URL + '/{},{}'.format(lat, lng))
    return response.json()
