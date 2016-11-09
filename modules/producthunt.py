# -*- coding: utf-8 -*- ?
import os
import json

import requests
import jinja2
import redis
import telegram

from libs.googleapis import shorten_url
from libs.timezone import local_time
from libs.utils import FakeMessage

PRODUCT_MESSAGE = jinja2.Template("*{{ product.name }}* _+{{ product.votes_count }} 🔥_\n\n"
                                  "{{ product.tagline }}\n\n{{ product.discussion_url }}")
DAILY_HUNT_HOURS = [13, 14, 15]

LOGIN_URL = 'https://api.producthunt.com/v1/oauth/token'
POSTS_URL = 'https://api.producthunt.com/v1/posts'

API_TOKEN = requests.post(
    LOGIN_URL,
    data={
        'client_id': os.environ['PRODUCTHUNT_API_KEY'],
        'client_secret': os.environ['PRODUCTHUNT_API_SECRET'],
        'grant_type': 'client_credentials'
    }
).json()['access_token']
PRODUCTS_TTL = 1800


def register(bot):
    bot.handlers["producthunt-get-entry"] = send_products

    bot.callback_handlers["producthunt-next-entry"] = next_entry
    bot.callback_handlers["producthunt-previous-entry"] = previous_entry

    bot.subscriptions.append({'name': 'daily-hunt', 'check': daily_hunt_check,
                              'send': daily_hunt_send})


def send_products(message, bot):
    products = get_products(bot)
    bot.user_set(message.u_id, "producthunt:cur_entry", 0)
    reply_message = PRODUCT_MESSAGE.render(product=products[0])
    reply_markup = build_result_keyboard(0, products[0], len(products))

    bot.telegram.send_message(message.u_id,
                              reply_message,
                              parse_mode=telegram.ParseMode.MARKDOWN,
                              reply_markup=reply_markup,
                              disable_web_page_preview=True)


def next_entry(query, bot):
    products = get_products(bot)
    next_entry = int(bot.user_get(query.u_id, "producthunt:cur_entry")) + 1
    bot.user_set(query.u_id, "producthunt:cur_entry", next_entry)
    edit_current_entry(products[next_entry], query, next_entry, len(products), bot)


def previous_entry(query, bot):
    products = get_products(bot)
    next_entry = int(bot.user_get(query.u_id, "producthunt:cur_entry")) - 1
    bot.user_set(query.u_id, "producthunt:cur_entry", next_entry)
    edit_current_entry(products[next_entry], query, next_entry, len(products), bot)


def get_products(bot):
    products = bot.redis.get("producthunt:cache")
    if products:
        products = json.loads(products.decode())
        return products

    response = requests.get(
        POSTS_URL,
        headers={'Authorization': 'Bearer {}'.format(API_TOKEN)}
    )
    products = response.json()['posts']

    for product in products:
        product['name'] = espace_markdown_symbols(product['name'])
        product['tagline'] = espace_markdown_symbols(product['tagline'])
        product['discussion_url'] = espace_markdown_symbols(shorten_url(product['discussion_url']))

    bot.redis.set("producthunt:cache", json.dumps(products))
    bot.redis.expire("producthunt:cache", PRODUCTS_TTL)

    return products


def edit_current_entry(entry, query, cur_page, products_num, bot):
    bot.telegram.editMessageText(
        text=PRODUCT_MESSAGE.render(product=entry),
        parse_mode=telegram.ParseMode.MARKDOWN,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=build_result_keyboard(cur_page, entry, products_num),
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )


def build_result_keyboard(cur_page, product, products_num):
    back_button = telegram.InlineKeyboardButton("⏮ Back", callback_data="producthunt-previous-entry")
    next_button = telegram.InlineKeyboardButton("Next ⏭­", callback_data="producthunt-next-entry")
    url_button = telegram.InlineKeyboardButton("Get it ❤️", url=product['redirect_url'])
    discussion_button = telegram.InlineKeyboardButton('Join discussion 💬', url=product['discussion_url'])

    keyboard = [[], [url_button, discussion_button]]
    if cur_page != 0:
        keyboard[0].append(back_button)
    if cur_page != products_num - 1:
        keyboard[0].append(next_button)

    return telegram.InlineKeyboardMarkup(keyboard)


# Product Hunt subscriptions


def daily_hunt_check(bot):
    result = []
    for key in bot.redis.scan_iter(match='user:*:notifications:producthunt:daily-hunt'):
        key = key.decode('utf-8')
        status = bot.redis.get(key).decode('utf-8')
        sent = bot.redis.get(key + ':sent')
        if status != '1' or (sent and sent.decode('utf-8') == '1'):
            continue
        _, user_id, _, _, _ = key.split(':')

        time = local_time(bot, int(user_id))

        if time.hour in DAILY_HUNT_HOURS:
            result.append(int(user_id))

    return result


def daily_hunt_send(bot, users):
    for u_id in users:
        key = 'user:{}:notifications:producthunt:daily-hunt:sent'.format(u_id)
        bot.redis.set(key, '1', ex=(len(DAILY_HUNT_HOURS) + 1) * 60 * 60)
        bot.telegram.send_message(u_id, 'Hey! That\'s your Product Hunt digest ☕')
        m = FakeMessage()
        m.u_id = u_id
        send_products(m, bot)


def espace_markdown_symbols(text):
    if not text:
        return ''
    for i in ['*', '_', '[', ']', '|']:
        text = text.replace(i, '\\' + i)
    return text
