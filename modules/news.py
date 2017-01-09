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

NEWS_MESSAGE = jinja2.Template("*{{entry.title}}*\n\n{{entry.description}}\n\n{{entry.url}}")
NEWS_API_URL = 'https://newsapi.org/v1/articles'
NEWS_API_TOKEN = os.environ['NEWSAPI_TOKEN']
NEWS_SOURCE = "google-news"
NEWS_TTL = 1800

NEWS_DIGEST_HOURS = [18, 19, 20]


def register(bot):
    bot.handlers["news-get-entry"] = send_news

    bot.callback_handlers["news-next-entry"] = next_entry
    bot.callback_handlers["news-last-entry"] = last_entry

    bot.subscriptions.append({'name': 'news-digest', 'check': news_digest_check,
                              'send': news_digest_send})


def send_news(message, bot):
    news = get_news(bot)
    bot.user_set(message.u_id, "news:cur_entry", 0)
    reply_message = NEWS_MESSAGE.render(entry=news[0])
    reply_markup = build_result_keyboard(0, news[0]["url"])

    bot.telegram.send_message(message.u_id,
                              reply_message,
                              parse_mode=telegram.ParseMode.MARKDOWN,
                              reply_markup=reply_markup,
                              disable_web_page_preview=True)


def next_entry(query, bot):
    news = get_news(bot)
    next_entry = int(bot.user_get(query.u_id, "news:cur_entry")) + 1
    bot.user_set(query.u_id, "news:cur_entry", next_entry)
    edit_current_entry(news[next_entry], query, next_entry, bot)


def last_entry(query, bot):
    news = get_news(bot)
    next_entry = int(bot.user_get(query.u_id, "news:cur_entry")) - 1
    bot.user_set(query.u_id, "news:cur_entry", next_entry)
    edit_current_entry(news[next_entry], query, next_entry, bot)


def get_news(bot, use_cache=True):
    news = bot.redis.get("news:cache")

    if news is None or not use_cache:
        news = requests.get(
            NEWS_API_URL,
            params={'source': NEWS_SOURCE, 'apiKey': NEWS_API_TOKEN}
        ).json()['articles']

        for article in news:
            article['title'] = espace_markdown_symbols(article['title'])
            article['description'] = espace_markdown_symbols(article['description'])
            article['url'] = espace_markdown_symbols(shorten_url(article['url']))

        bot.redis.set("news:cache", json.dumps(news))
        bot.redis.expire("news:cache", NEWS_TTL)
    else:
        news = json.loads(news.decode())

    return news


def edit_current_entry(entry, query, cur_page, bot):
    bot.telegram.editMessageText(
        text=NEWS_MESSAGE.render(entry=entry),
        parse_mode=telegram.ParseMode.MARKDOWN,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=build_result_keyboard(cur_page, entry["url"]),
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )


def build_result_keyboard(cur_page, article_url):
    back_button = telegram.InlineKeyboardButton("⏮ Back", callback_data="news-last-entry")
    next_button = telegram.InlineKeyboardButton("Next ⏭­", callback_data="news-next-entry")
    url_button = telegram.InlineKeyboardButton("Open article 🌐", url=article_url)

    keyboard = [[], [url_button]]
    if cur_page != 0:
        keyboard[0].append(back_button)
    if cur_page != 9:
        keyboard[0].append(next_button)

    return telegram.InlineKeyboardMarkup(keyboard)


# News subscription


def news_digest_check(bot):
    result = []
    for key in bot.redis.scan_iter(match='user:*:notifications:news:news-digest'):
        key = key.decode('utf-8')
        status = bot.redis.get(key).decode('utf-8')
        sent = bot.redis.get(key + ':sent')
        if status != '1' or (sent and sent.decode('utf-8') == '1'):
            continue
        _, user_id, _, _, _ = key.split(':')

        time = local_time(bot, int(user_id))

        if time and time.hour in NEWS_DIGEST_HOURS:
            result.append(int(user_id))

    return result


def news_digest_send(bot, users):
    for u_id in users:
        try:
            key = 'user:{}:notifications:news:news-digest:sent'.format(u_id)
            bot.redis.set(key, '1', ex=(len(NEWS_DIGEST_HOURS) + 1) * 60 * 60)
            bot.telegram.send_message(u_id, 'Hey, your evening news digest is ready 📰')
            m = FakeMessage()
            m.u_id = u_id
            send_news(m, bot)
        except Exception as error:
            bot.logger.error(error)


def espace_markdown_symbols(text):
    if not text:
        return ''
    for i in ['*', '_', '[', ']', '|']:
        text = text.replace(i, '\\' + i)
    return text
