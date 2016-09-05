import os
import logging
from time import sleep

import telegram
from telegram.error import NetworkError, Unauthorized

from leonard import Leonard

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)

try:
    update_id = telegram_client.getUpdates()[0].update_id
except IndexError:
    update_id = None

while True:
    try:
        for update in telegram_client.getUpdates(offset=update_id, timeout=10):
            # chat_id is required to reply to any message
            chat_id = update.message.chat_id
            update_id = update.update_id + 1

            if update.message:  # your bot can receive updates without messages
                # Reply to the message
                telegram_client.sendMessage(chat_id=chat_id, text=update.message.text)
    except NetworkError:
        sleep(1)
    except Unauthorized:
        # The user has removed or blocked the bot.
        update_id += 1