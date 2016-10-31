import time
import requests
import telegram

from libs.utils import build_bot
from modules.uber import CURRENT_ORDER_URL, UPDATE_CARD

bot = build_bot()

while True:
    for u_id in bot.redis.sscan_iter('uber:requested_users'):
        u_id = int(u_id)
        token = bot.user_get(u_id, 'uber:access_token')
        response = requests.get(CURRENT_ORDER_URL, headers={
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json',
        }).json()
        if 'errors' in response:
            response['status'] = 'completed'
            bot.redis.srem('uber:requested_users', u_id)
        if response['status'] == 'processing':
            continue
        if response['status'] != bot.user_get(u_id, 'uber:request_stage'):
            bot.user_set(u_id, 'uber:request_stage', response['status'])
            bot.telegram.send_message(u_id, UPDATE_CARD.render(data=response),
                                      parse_mode=telegram.ParseMode.MARKDOWN)
        time.sleep(0.5)
    time.sleep(5)
