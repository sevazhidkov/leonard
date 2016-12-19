import os
import time

import telegram

from leonard import Leonard

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()


def main():
    for subscription in bot.subscriptions:
        try:
            subscription['send'](bot, subscription['check'](bot))
        except Exception as error:
            bot.logger.error(error)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        bot.logger.error(e)
