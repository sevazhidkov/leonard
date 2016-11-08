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

DARKSKY_MESSAGE = 'Weather information provided by DarkSky.net'
WEATHER_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nToday: _{{ today_date.format('MMMM DD, YYYY') }}_\n\n"
                                  "Right now: *{{ temperature }} {{ temperature_symbol }}*, _{{ summary|lower }}_ "
                                  "{{ emoji }}\n{{ day_summary }}\n\nTomorrow: "
                                  "*{{ tomorrow_temperature }} {{ temperature_symbol }}*, "
                                  "_{{ tomorrow_summary|lower }}_ {{ tomorrow_emoji }}"
                                  "\n\n[Powered by Dark Sky](https://darksky.net/poweredby/)")
HOURS_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nHourly forecast: 🕘\n\n{% for hour in hours %}"
                                   "_{{ hour.time }}_ – *{{ hour.temperature|round(2) }} {{ temperature_symbol }}*, "
                                   "_{{ hour.summary|lower }}_ {{ hour.emoji }}\n{% endfor %}")
WEEK_MESSAGE = jinja2.Template("⛅ ☁️ ☔\nWeek weather: 📅\n\n{% for day in days %}"
                                   "_{{ day.time.format('MMMM DD, dddd') }}_ – "
                                   "*{{ day.temperature|round(1) }} {{ temperature_symbol }}*, "
                                   "{{ day.summary|lower }} {{ day.emoji }}\n{% endfor %}")

RAIN_SOON = jinja2.Template("☔ ☔ ☔\nThere will be rain soon:\n\n{% for hour in hours %}"
                            "{{ hour.time }} – *{{ hour.temperature }} ℉*, "
                            "_{{ hour.summary|lower }}_ {{ hour.emoji }}\n{% endfor %}")
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


def register(bot):
    bot.handlers['weather-show'] = show_weather
    bot.callback_handlers['weather-basic'] = basic_forecast_callback
    bot.callback_handlers['weather-hourly'] = hour_forecast_callback
    bot.callback_handlers['weather-week'] = week_forecast_callback


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
            'temperature': ((weather_data['daily']['data'][1]['temperatureMax'] +
                                  weather_data['daily']['data'][1]['temperatureMin']) / 2),
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


def get_weather(lat, lng):
    response = requests.get(
        ENDPOINT_URL + '/{},{}'.format(lat, lng),
        params={
            'units': 'auto'
        }
    )
    return response.json()
