import os
import time

import telegram

from leonard import Leonard

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()

if __name__ == '__main__':
    for subscription in bot.subscriptions:
        subscription['send'](bot, subscription['check'](bot))
