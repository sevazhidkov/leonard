import os
import time

import telegram

from leonard import Leonard

if __name__ == '__main__':
    os.chdir('../')
    telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
    bot = Leonard(telegram_client)
    bot.collect_plugins()
    while True:
        for name, check, send in bot.subscriptions:
            send(bot, check(bot))
        time.sleep(60)
