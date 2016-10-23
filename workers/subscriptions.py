import os

import telegram

from leonard import Leonard

if __name__ == '__main__':
    os.chdir('../')
    telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
    bot = Leonard(telegram_client)
    i = 0
    while True:
        if i % 10 == 0:
            bot.collect_plugins()
        for name, check, send in bot.subscriptions:
            send(bot, check(bot))
        i += 1
