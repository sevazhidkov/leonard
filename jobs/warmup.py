import os

import telegram

from leonard import Leonard
from modules.news import get_news
from modules.producthunt import get_products

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()

get_news(bot, use_cache=False)
get_products(bot, use_cache=False)
