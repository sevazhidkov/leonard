import os
import json
import sys
import logging
from time import sleep

import bugsnag
import tornado.web
from bugsnag.tornado import BugsnagRequestHandler
from urllib.parse import quote_plus

import telegram
from telegram.error import NetworkError, Unauthorized, RetryAfter

from leonard import Leonard
from libs import shrt

WEBHOOK_HOSTNAME = os.environ.get('WEBHOOK_HOSTNAME', 'https://leonardbot.herokuapp.com')


class WebhookHandler(BugsnagRequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)

    def initialize(self, **kwargs):
        self.bot = kwargs['bot']

    def post(self):
        if self.request.headers.get('Content-Length') in (None, 0):
            # Nothing to do
            return

        # Read the request body.
        body = self.request.body
        if not body:
            raise tornado.web.HTTPError(400, 'A valid JSON document is required.')

        try:
            content = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise tornado.web.HTTPError(753, 'Could not decode the request body. The '
                                             'JSON was incorrect or not encoded as '
                                             'UTF-8.')

        update = telegram.Update.de_json(content, self.bot.telegram)
        self.bot.process_update(update)

        self.write('ok')


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
bot.tornado.add_handlers(r'.*', [
    (r'/webhook/{}'.format(quote_plus(os.environ['BOT_TOKEN'])), WebhookHandler, {'bot': bot})
])
bot.tornado.add_handlers(r'.*', [
    (r'/l/{query}', shrt.GetLinkHandler)
])

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
        except NetworkError as error:
            bugsnag.notify(error)
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