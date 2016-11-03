import os
import json
import sys
import logging
from time import sleep

import falcon

import telegram
from telegram.error import NetworkError, Unauthorized, RetryAfter

from leonard import Leonard
from libs import shrt

WEBHOOK_HOSTNAME = os.environ.get('WEBHOOK_HOSTNAME', 'https://leonardbot.herokuapp.com')


class WebhookResource:
    def __init__(self, bot):
        self.bot = bot


    def on_post(self, req, resp):
        if req.content_length in (None, 0):
            # Nothing to do
            return

        # Read the request body.
        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        try:
            content = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')

        update = telegram.Update.de_json(content, self.bot.telegram)
        bot.process_update(update)

        resp.body = 'ok'


debug = False
if 'BOT_DEBUG' in os.environ and os.environ['BOT_DEBUG'] == '1':
    debug = True

print('Starting bot')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('leonard')
logger.setLevel(logging.INFO)

print('Creating bot')
telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client, debug)

print('Collecting plugins')
bot.collect_plugins()

print('Setting routes')
bot.app.add_route('/webhook/{}'.format(os.environ['BOT_TOKEN']), WebhookResource(bot))
bot.app.add_route('/l/{query}', shrt.GetLinkResource())

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

print('Setting webhook')

# Register webhook
webhook_url = WEBHOOK_HOSTNAME + '/webhook/' + os.environ['BOT_TOKEN']
try:
    bot.telegram.setWebhook(webhook_url)
except (NetworkError, RetryAfter):
    sleep(1)
    bot.telegram.setWebhook(webhook_url)
