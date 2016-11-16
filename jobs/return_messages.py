import os
import random
import logging

import arrow
import telegram
from telegram.error import Unauthorized

from leonard import Leonard
from modules.menu import GREETING_PHRASES
from libs.timezone import local_time
from libs.utils import FakeMessage

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()

RETURN_MESSAGE_HOURS = list(range(11, 20))
RETURN_MESSAGE = '{} {}\n{}'

HOUR_MESSAGES = [(range(11, 17), 'Have a nice day ❤️'),
                 (range(17, 20), 'Good evening!')]
ASSIST_MESSAGES = ['By the way, if you have problems with me, you can write my developer @sevazhidkov',
                   'You can unsubscribe from such messages using Subscriptions 📬']


def main():
    for key in bot.redis.scan_iter(match='user:*:registered'):
        if bot.redis.get(key).decode('utf-8') != '1':
            # TODO: Add reminder about registration
            continue
        _, u_id, _ = key.decode('utf-8').split(':')

        status = bot.user_get(u_id, 'notifications:returns:messages')
        if status == '0':
            continue

        time = local_time(bot, int(u_id))
        if time.hour not in RETURN_MESSAGE_HOURS:
            continue

        if bot.user_get(u_id, 'return_sent'):
            continue

        return_hour = bot.user_get(u_id, 'return_hour')
        if return_hour and time.hour != int(return_hour):
            continue
        elif not return_hour:
            # Choose hour for return message
            hour = random.choice(RETURN_MESSAGE_HOURS)
            bot.user_set(u_id, 'return_hour', hour)
            if hour != time.hour:
                continue

        last_interaction = arrow.get(bot.user_get(u_id, 'last_interaction') or time)
        interaction_delta = time - last_interaction

        if interaction_delta and last_interaction.replace(hours=+1) > time:
            continue

        bot.logger.info('Checking return message to: {}, where list: {}'.format(
            u_id, ([0] * round(interaction_delta.days / 2) + [0]) + [1, 1]
        ))

        result = random.choice(([0] * round(interaction_delta.days / 2) + [0]) + [1, 1])
        bot.user_set(u_id, 'return_sent', time.timestamp, ex=len(RETURN_MESSAGE_HOURS) * 60 * 60)
        if result != 1:
            continue

        m = FakeMessage()
        m.u_id = u_id
        for interval, message  in HOUR_MESSAGES:
            if time.hour in interval:
                hour_message = message

        try:
            bot.call_handler(m, 'main-menu', phrase=RETURN_MESSAGE.format(
                hour_message, random.choice(GREETING_PHRASES), random.choice(ASSIST_MESSAGES)
            ))
        except Unauthorized:
            bot.logger.warning('Unauthorized for {}'.format(u_id))
        except Exception as error:
            bot.logger.error(error)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        bot.logger.error(e)
