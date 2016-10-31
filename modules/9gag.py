import collections
from random import choice

from boto3.dynamodb.conditions import Attr
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from leonard import Leonard

NAME = '9GAG'

SUBSCRIBES = collections.OrderedDict([
    ('New memes every hour 🌇', [
        'meme-hour',
        ('Well, now every morning I will send weather forecasts specially for you ☺️',
         'No more morning forecasts, honey.'),
    ]),
])


def register(bot):
    bot.handlers['meme-show'] = show_meme

    bot.subscriptions.append(('{}:{}'.format(NAME, list(SUBSCRIBES.values())[0][0]), check_show_meme_hour, send_meme))


def check_show_meme_hour(bot: Leonard):
    key = list(SUBSCRIBES.values())[0][0]
    users = bot.redis.keys('user:*:notifications:{}:{}'.format(NAME, key))
    users = list(map(lambda x: x.decode('utf-8').split(':')[1], users)) if users else []
    result = []
    for u_id in users:
        if (bot.redis.ttl('user:{}:notifications:{}:{}:last'.format(u_id, NAME, key)) or 0) <= 0:
            result.append(u_id)
            bot.redis.setex('user:{}:notifications:{}:{}:last'.format(u_id, NAME, key), 1, 60 * 60)
    return users


def send_meme(bot: Leonard, users):
    for u_id in users:
        show_meme(None, bot, u_id, )


def show_meme(message, bot: Leonard, user_id=None):
    if message:
        user_id = message.u_id
    title, img, post_id = get_meme(bot, user_id)
    bot.telegram.send_photo(
        user_id,
        photo=img,
        caption=title,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Open on 9GAG', url='9gag.com/gag/' + post_id)]])
    )


def get_meme(bot: Leonard, user_id):
    meme = choice(bot.nine_gag.scan(
        FilterExpression=~Attr('viewed').contains(user_id)
    )['Items'])
    bot.nine_gag.update_item(
        Key={
            'postId': meme['postId']
        },
        UpdateExpression="set viewed = list_append(viewed, :user_id)",
        ExpressionAttributeValues={
            ':user_id': [user_id]
        }
    )
    return meme['title'], meme['img'], meme['postId']
