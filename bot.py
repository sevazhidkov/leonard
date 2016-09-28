import os
import logging
from time import sleep

import telegram
from telegram.error import NetworkError, Unauthorized

from leonard import Leonard

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('leonard')
logger.setLevel(logging.INFO)

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()

# Start polling
try:
    update_id = telegram_client.getUpdates()[0].update_id
except IndexError:
    update_id = None

while True:
    try:
        for update in telegram_client.getUpdates(offset=update_id, timeout=10):
            chat_id = update.message.chat_id
            update_id = update.update_id + 1

            bot.process_update(update)
    except NetworkError:
        sleep(1)
    except Unauthorized:
        update_id += 1
