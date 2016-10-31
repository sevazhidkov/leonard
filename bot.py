import os
import sys
import logging
from time import sleep

from flask import request

import telegram
from telegram.error import NetworkError, Unauthorized

from leonard import Leonard
from libs import shrt

WEBHOOK_HOSTNAME = os.environ.get('WEBHOOK_HOSTNAME', 'https://leonardbot.herokuapp.com')

debug = False
if 'BOT_DEBUG' in os.environ and os.environ['BOT_DEBUG'] == '1':
    debug = True

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('leonard')
logger.setLevel(logging.INFO)

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client, debug)
bot.collect_plugins()


@bot.app.route('/webhook/<token>', methods=['POST'])
def webhook(token):
    if token != os.environ['BOT_TOKEN']:
        return 'bad token'
    update = telegram.Update.de_json(request.get_json(force=True), bot.telegram)
    bot.process_update(update)
    return 'ok'

shrt.get_link_route = bot.app.route('/l/<query>')(shrt.get_link_route)

if len(sys.argv) > 1 and sys.argv[1] == 'polling':
    bot.telegram.setWebhook('')
    try:
        update_id = telegram_client.getUpdates()[0].update_id
    except IndexError:
        update_id = None

    while True:
        try:
            for update in telegram_client.getUpdates(offset=update_id, timeout=10):
                update_id = update.update_id + 1
                bot.process_update(update)
        except NetworkError:
            sleep(1)
        except Unauthorized:
            update_id += 1
    exit()

# Register webhook
webhook_url = WEBHOOK_HOSTNAME + '/webhook/' + os.environ['BOT_TOKEN']
try:
    bot.telegram.setWebhook(webhook_url)
except NetworkError:
    sleep(1)
    bot.telegram.setWebhook(webhook_url)

if __name__ == '__main__':
    bot.app.run(port=8888)
