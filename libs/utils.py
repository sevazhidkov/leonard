import os
import time
import telegram
from leonard import Leonard


class FakeMessage:
    pass


def build_bot():
    telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
    bot = Leonard(telegram_client)
    bot.collect_plugins()
    return bot
