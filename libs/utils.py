import os
import telegram
from leonard import Leonard


def build_bot():
    telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
    bot = Leonard(telegram_client)
    bot.collect_plugins()
    return bot
