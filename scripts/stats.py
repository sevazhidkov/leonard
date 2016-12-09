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

    notifications_count = {}
    for key in bot.redis.scan_iter(match='user:*:notifications:*'):
        key = key.decode('utf-8')
        print(key)
        _, _, _, group, name = key.split(':')
        notification = '{}:{}'.format(group, name)
        notifications_count[notification] = notifications_count.get(notification, 0) + 1

    print('Total users:', count, end='\n\n')

    print('Notifications:')
    for notification, n in list(sorted(notifications_count.items(), key=lambda x: x[1])):
        print(notification, '-', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        bot.logger.error(e)
