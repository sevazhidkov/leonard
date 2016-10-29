import os
import json

import requests
import jinja2
import redis
import telegram

NEWS_MESSAGE = jinja2.Template("*{{entry.title}}*\n\n{{entry.description}}\n\n{{entry.url}}")
NEWS_API_URL = jinja2.Template("https://newsapi.org/v1/articles?source={{source}}&apiKey={{api_key}}")
NEWS_API_TOKEN = os.environ.get("NEWS_API_TOKEN","7a29c414291346f1bb49dac6924216a4")
NEWS_SOURCE = "google-news"
NEWS_TTL = 9000

def register(bot):
    bot.handlers["news_get_entry"] = send_news

    bot.callback_handlers["news_next_entry"] = next_entry
    bot.callback_handlers["news_last_entry"] = last_entry

def send_news(message, bot):
    news = get_news(bot)
    bot.user_set(message.u_id, "news:cur_entry", 0)
    reply_message = NEWS_MESSAGE.render(entry=news[0])
    reply_markup = build_result_keyboard()
    
    bot.telegram.send_message(message.u_id, reply_message, 
                              parse_mode = telegram.ParseMode.MARKDOWN,
                              reply_markup = reply_markup) 

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

def get_news(bot):
    news = bot.redis.get("news:cache")
    
    if news is None:
        request = requests.get(NEWS_API_URL.render(source = NEWS_SOURCE, api_key = NEWS_API_TOKEN)).text
        news = json.loads(request)["articles"]
        bot.redis.set("news:cache",json.dumps(news))
        bot.redis.expire("news:cache",NEWS_TTL)
    else:
        news = json.loads(news.decode())    

    return news 

def edit_current_entry(entry, query, cur_page, bot):
    bot.telegram.editMessageText(
        text = NEWS_MESSAGE.render(entry=entry),
        parse_mode = telegram.ParseMode.MARKDOWN,
        chat_id = query.message.chat_id,
        message_id = query.message.message_id
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup = build_result_keyboard(cur_page),
        chat_id = query.message.chat_id,
        message_id = query.message.message_id
    )


def build_result_keyboard(cur_page=0):
    back_button = telegram.InlineKeyboardButton("⏮ Back", callback_data="news_last_entry")
    next_button = telegram.InlineKeyboardButton("Next ⏭", callback_data="news_next_entry")
    
    keyboard = [[],[]]
    if cur_page != 0:
        keyboard[0].append(back_button)
    if cur_page != 9:
        keyboard[0].append(next_button)
        
    return telegram.InlineKeyboardMarkup(keyboard)