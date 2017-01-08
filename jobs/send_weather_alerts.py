import json
import logging
import os
import datetime

import requests
import telegram

from leonard import Leonard

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()

ENDPOINT_URL = 'https://api.darksky.net/forecast/{}'.format(os.environ['DARKSKY_TOKEN'])


def main():
    if datetime.datetime.now().hour % 6 != 0:
        return
    for key in bot.redis.scan_iter(match='user:*[0-9]:location'):
        user_id = key.decode('utf-8').split(':')[1]
        location = json.loads(bot.user_get(user_id, 'location'))
        weather = requests.get(
            ENDPOINT_URL + '/{},{}'.format(location['lat'], location['long']),
            params={
                'units': 'auto'
            }
        ).json()
        if 'alerts' in weather:
            for alert in weather['alerts']:
                bot.send_message(user_id, text=alert['title'] + '\n\n\n' + alert['description'])


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(e)
