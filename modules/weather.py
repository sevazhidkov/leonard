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

from libs.utils import FakeMessage
from libs.timezone import local_time

DARKSKY_MESSAGE = 'Weather information provided by DarkSky.net'
WEATHER_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nToday: _{{ today_date.format('MMMM DD, YYYY') }}_\n\n"
                                  "Right now: *{{ temperature }} {{ temperature_symbol }}*, _{{ summary|lower }}_ "
                                  "{{ emoji }}\n{{ day_summary }}\n\nTomorrow: "
                                  "*{{ tomorrow_temperature|round(1) }} {{ temperature_symbol }}*, "
                                  "_{{ tomorrow_summary|lower }}_ {{ tomorrow_emoji }}"
                                  "\n\n[Powered by Dark Sky](https://darksky.net/poweredby/)")
HOURS_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nHourly forecast: 🕘\n\n{% for hour in hours %}"
                                   "_{{ hour.time }}_ – *{{ hour.temperature|round(2) }} {{ temperature_symbol }}*, "
                                   "_{{ hour.summary|lower }}_ {{ hour.emoji }}\n{% endfor %}")
WEEK_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nWeek weather: 📅\n\n{% for day in days %}"
                                   "_{{ day.time.format('MMMM DD, dddd') }}_ – "
                                   "*{{ day.temperature|round(1) }} {{ temperature_symbol }}*, "
                                   "{{ day.summary|lower }} {{ day.emoji }}\n{% endfor %}")

RAIN_SOON = jinja2.Template("☔ Hey, today will be rain! Don't forget your umbrella! \n\n{% for hour in hours %}"
                            "_{{ hour.time }}_ – *{{ hour.temperature|round(2) }} {{ hour.symbol }}*, "
                            "{{ hour.summary|lower }} {{ hour.emoji }}\n{% endfor %}")
ENDPOINT_URL = 'https://api.darksky.net/forecast/{}'.format(os.environ['DARKSKY_TOKEN'])

BASIC_FORECAST_BUTTON = 'Summary 🌀'
HOURS_FORECAST_BUTTON = 'Hourly 🕘'
WEEK_FORECAST_BUTTON = 'Week 📅'

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
UNITS_SYMBOLS = {
    'si': '°C',
    'us': '℉'
}

MORNING_FORECAST_HOURS = [8, 9, 10]
RAIN_NOTIFICATIONS_HOURS = [7, 8, 9, 18]


def register(bot):
    bot.handlers['weather-show'] = show_weather

    bot.callback_handlers['weather-basic'] = basic_forecast_callback
    bot.callback_handlers['weather-hourly'] = hour_forecast_callback
    bot.callback_handlers['weather-week'] = week_forecast_callback

    bot.subscriptions.append({'name': 'morning-forecast', 'check': morning_forecast_check,
                              'send': morning_forecast_send})
    bot.subscriptions.append({'name': 'rain-notifications', 'check': rain_notifications_check,
                              'send': rain_notifications_send})


def show_weather(message, bot, subscription=False):
    basic_forecast = build_basic_forecast(message.u_id, bot)
    bot.telegram.send_message(
        message.u_id, basic_forecast[0],
        parse_mode=telegram.ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=basic_forecast[1]
    )


def basic_forecast_callback(query, bot):
    basic_forecast = build_basic_forecast(query.u_id, bot)
    bot.telegram.editMessageText(
        text=basic_forecast[0],
        parse_mode=telegram.ParseMode.MARKDOWN,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=basic_forecast[1],
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )


def build_basic_forecast(user_id, bot):
    location = json.loads(bot.user_get(user_id, 'location'))
    weather_data = get_weather(location['lat'], location['long'])
    bot.user_set(user_id, 'weather:data', json.dumps(weather_data))
    reply_markup = telegram.InlineKeyboardMarkup(
        [[telegram.InlineKeyboardButton(HOURS_FORECAST_BUTTON, callback_data='weather-hourly'),
          telegram.InlineKeyboardButton(WEEK_FORECAST_BUTTON, callback_data='weather-week')]]
    )
    weather_message = WEATHER_MESSAGE.render(
        today_date=arrow.get(weather_data['currently']['time']),
        temperature_symbol=UNITS_SYMBOLS.get(weather_data['flags']['units'], '°C'),
        temperature=weather_data['currently']['temperature'],
        summary=weather_data['currently']['summary'],
        emoji=WEATHER_ICONS.get(weather_data['currently']['icon'], ''),
        day_summary=weather_data['hourly']['summary'],
        tomorrow_temperature=((weather_data['daily']['data'][1]['temperatureMax'] +
                              weather_data['daily']['data'][1]['temperatureMin']) / 2),
        tomorrow_summary=weather_data['daily']['data'][1]['summary'],
        tomorrow_emoji=WEATHER_ICONS.get(weather_data['daily']['data'][1]['icon'], '')
    )
    return weather_message, reply_markup


def hour_forecast_callback(query, bot):
    hour_forecast = build_hour_forecast(query.u_id, bot)
    bot.telegram.editMessageText(
        text=hour_forecast[0],
        parse_mode=telegram.ParseMode.MARKDOWN,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=hour_forecast[1],
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )


def build_hour_forecast(user_id, bot):
    weather_data = json.loads(bot.user_get(user_id, 'weather:data'))
    reply_markup = telegram.InlineKeyboardMarkup(
        [[telegram.InlineKeyboardButton(BASIC_FORECAST_BUTTON, callback_data='weather-basic'),
          telegram.InlineKeyboardButton(WEEK_FORECAST_BUTTON, callback_data='weather-week')]]
    )
    hours = []
    for i in range(0, min(24, len(weather_data['hourly']['data'])), 2):
        hour = weather_data['hourly']['data'][i]
        hours.append({
            'time': arrow.get(hour['time']).to(weather_data['timezone']).format('H:00'),
            'temperature': hour['temperature'],
            'summary': hour['summary'],
            'emoji': WEATHER_ICONS.get(hour['icon'], '')
        })
    message = HOURS_MESSAGE.render(
        hours=hours,
        temperature_symbol=UNITS_SYMBOLS.get(weather_data['flags']['units'], '°C')
    )
    return message, reply_markup


def week_forecast_callback(query, bot):
    week_forecast = build_week_forecast(query.u_id, bot)
    bot.telegram.editMessageText(
        text=week_forecast[0],
        parse_mode=telegram.ParseMode.MARKDOWN,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=week_forecast[1],
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )


def build_week_forecast(user_id, bot):
    weather_data = json.loads(bot.user_get(user_id, 'weather:data'))
    reply_markup = telegram.InlineKeyboardMarkup(
        [[telegram.InlineKeyboardButton(HOURS_FORECAST_BUTTON, callback_data='weather-hourly'),
          telegram.InlineKeyboardButton(BASIC_FORECAST_BUTTON, callback_data='weather-basic')]]
    )
    days = []
    for day in weather_data['daily']['data'][1:]:
        days.append({
            'time': arrow.get(day['time']).to(weather_data['timezone']),
            'temperature': ((day['temperatureMax'] + day['temperatureMin']) / 2),
            'summary': day['summary'],
            'emoji': WEATHER_ICONS.get(day['icon'], '')
        })
    message = WEEK_MESSAGE.render(
        days=days,
        temperature_symbol=UNITS_SYMBOLS.get(weather_data['flags']['units'], '°C')
    )
    return message, reply_markup


# Morning forecast subscription


def morning_forecast_check(bot):
    result = []

    for key in bot.redis.scan_iter(match='user:*:notifications:weather:morning-forecast'):
        key = key.decode('utf-8')
        status = bot.redis.get(key).decode('utf-8')
        sent = bot.redis.get(key + ':sent')
        if status != '1' or (sent and sent.decode('utf-8') == '1'):
            continue
        _, user_id, _, _, _ = key.split(':')

        if not bot.user_get(user_id, "location"): continue

        time = local_time(bot, int(user_id))

        if time and time.hour in MORNING_FORECAST_HOURS:
            result.append(int(user_id))

    return result


def morning_forecast_send(bot, users):
    for u_id in users:
        try:
            bot.telegram.send_message(u_id, 'Good morning, here is today weather forecast for you ❤️')
            message = FakeMessage()
            message.u_id = u_id
            bot.call_handler(message, 'weather-show')
            key = 'user:{}:notifications:weather:morning-forecast:sent'.format(u_id)
            bot.redis.set(key, '1', ex=(len(MORNING_FORECAST_HOURS) + 1) * 60 * 60)
        except Exception as error:
            bot.logger.error(error)


# Rain notification subscription


def rain_notifications_check(bot):
    result = []

    for key in bot.redis.scan_iter(match='user:*:notifications:weather:rain-notifications'):
        key = key.decode('utf-8')
        status = bot.redis.get(key).decode('utf-8')
        if status != '1':
            continue

        _, user_id, _, _, _ = key.split(':')

        if not bot.user_get(user_id, "location"): continue

        time = local_time(bot, int(user_id))

        if not time or time.hour not in RAIN_NOTIFICATIONS_HOURS:
            continue

        checked = bot.redis.get(key + ':checked')  # Did we already checked for rain in this day
        if checked and checked.decode('utf-8') == '1':
            continue

        location = json.loads(bot.user_get(int(user_id), 'location'))
        weather_data = get_weather(location['lat'], location['long'])

        rain_hours = []
        for hour in weather_data['hourly']['data']:
            if arrow.get(hour['time']).day != time.day:
                continue

            if ('precipProbability' in hour and hour['precipProbability'] > 0.5 and
                'precipType' in hour and hour['precipType'] in ['rain', 'sleet']):
                rain_hours.append({
                    'time': arrow.get(hour['time']).to(weather_data['timezone']).format('H:00'),
                    'temperature': hour['temperature'],
                    'summary': hour['summary'],
                    'emoji': WEATHER_ICONS.get(hour['icon'], ''),
                    'symbol': UNITS_SYMBOLS.get(weather_data['flags']['units'], '°C')
                })

        if rain_hours:
            bot.user_set(int(user_id), 'weather:rain_hours', json.dumps(rain_hours))
            result.append(int(user_id))
        bot.redis.set(key + ':checked', '1', ex=(len(RAIN_NOTIFICATIONS_HOURS) + 1) * 60 * 60)

    return result


def rain_notifications_send(bot, users):
    reply_markup = telegram.InlineKeyboardMarkup(
        [[telegram.InlineKeyboardButton(BASIC_FORECAST_BUTTON, callback_data='weather-basic'),
          telegram.InlineKeyboardButton(HOURS_FORECAST_BUTTON, callback_data='weather-hourly')]]
    )
    for u_id in users:
        try:
            rain_hours = json.loads(bot.user_get(u_id, 'weather:rain_hours'))
            bot.telegram.send_message(
                u_id, RAIN_SOON.render(hours=rain_hours),
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN
            )
        except Exception as error:
            bot.logger.error(error)


def get_weather(lat, lng):
    response = requests.get(
        ENDPOINT_URL + '/{},{}'.format(lat, lng),
        params={
            'units': 'auto'
        }
    )
    return response.json()
