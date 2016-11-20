import os
import telegram
from leonard import Leonard

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()


def main():
    count = 0
    for key in bot.redis.scan_iter(match='user:*:registered'):
        count += 1

    print('Total users:', count)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        bot.logger.error(e)
