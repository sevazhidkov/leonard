import os
import time
import requests
import telegram
from leonard import Leonard


class FakeMessage:
    pass


def build_bot():
    telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
    bot = Leonard(telegram_client)
    bot.collect_plugins()
    return bot


def get_timezone(lat, long):
    response = requests.get('https://maps.googleapis.com/maps/api/timezone/json', params={
        'location': '{},{}'.format(lat, long),
        'timestamp': int(time.time()),
        'key': os.environ['GOOGLE_API_TOKEN']
    }).json()
    return response['timeZoneId']
