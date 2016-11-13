import os
import random
import logging

import arrow
import telegram

from leonard import Leonard
from libs.timezone import local_time
from libs.utils import FakeMessage

telegram_client = telegram.Bot(os.environ['BOT_TOKEN'])
bot = Leonard(telegram_client)
bot.collect_plugins()

RETURN_MESSAGE_HOURS = list(range(8, 22))


def main():
    for key in bot.redis.scan_iter(match='user:*:registered'):
        if bot.redis.get(key).decode('utf-8') != '1':
            # TODO: Add reminder about registration
            continue
        _, u_id, _ = key.decode('utf-8').split(':')

        time = local_time(bot, int(u_id))
        if time.hour not in RETURN_MESSAGE_HOURS:
            continue

        if bot.user_get(u_id, 'return_sent') == '1':
            continue

        last_interaction = arrow.get(bot.user_get(u_id, 'last_interaction') or time)
        interaction_delta = time - last_interaction

        # if interaction_delta and last_interaction.replace(hours=+1) > time:
            # continue

        bot.logger.info('Checking return message to: {}, where list: {}'.format(
            u_id, ([0] * round(interaction_delta.days / 2) + [0]) + [1, 1]
        ))

        result = random.choice(([0] * round(interaction_delta.days / 2) + [0]) + [1, 1])
        if result != 1:
            continue

        bot.user_set(u_id, 'return_sent', '1', ex=len(RETURN_MESSAGE_HOURS) * 60 * 60)
        m = FakeMessage()
        m.u_id = u_id
        bot.call_handler(m, 'main-menu')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(e)
