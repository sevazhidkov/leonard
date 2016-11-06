import collections
import json
from random import choice

import arrow
import pytz
import boto3
from boto3.dynamodb.conditions import Attr, AttributeNotExists
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from leonard import Leonard

NAME = '9GAG'
ORDER = 2

SUBSCRIBES = collections.OrderedDict([
    ('New memes every day 🤗', [
        'meme-day',
        ('Now next day will be happier than previous! 😀',
         'No more daily memes, unfortunately. 😓'),
        (10, 11, 12)
    ]),
])

dynamo = boto3.resource('dynamodb', 'eu-west-1')


def register(bot):
    bot.nine_gag = dynamo.Table('LeonardBot9gagPosts')

    bot.handlers['meme-show'] = show_meme

    bot.subscriptions.append((
        '{}:{}'.format(NAME, list(SUBSCRIBES.values())[0][0]),
        check_show_meme_day,
        send_meme_day
    ))


def check_show_meme_day(bot: Leonard):
    key = list(SUBSCRIBES.values())[0][0]
    users = bot.redis.keys('user:*:notifications:{}:{}'.format(NAME, key))
    users = list(map(lambda x: x.decode('utf-8').split(':')[1], users)) if users else []
    result = []
    for u_id in users:
        location = bot.user_get(u_id, 'location')
        if not location:
            timezone = pytz.timezone('UTC')
        else:
            user = json.loads(location)
            timezone = pytz.timezone(user['timezone'])
        if arrow.now(timezone).datetime.hour in list(SUBSCRIBES.values())[0][2] and (
                    bot.redis.ttl('user:{}:notifications:{}:{}:last'.format(u_id, NAME, key)) or 0) <= 0:
            result.append(u_id)
            bot.redis.setex('user:{}:notifications:{}:{}:last'.format(u_id, NAME, key), 1, 24 * 60 * 60)
    return result


def send_meme_day(bot: Leonard, users):
    for u_id in users:
        bot.telegram.send_message(u_id, 'Here is your daily meme, my friend! 😆')
        show_meme(None, bot, u_id)


def show_meme(message, bot: Leonard, user_id=None):
    if message:
        user_id = message.u_id
    title, img, post_id = get_meme(bot, user_id)
    photos = bot.telegram.send_photo(
        user_id,
        photo=img,
        caption=title,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Open on 9GAG', url='9gag.com/gag/' + post_id)]])
    )

    if bot.debug:
        file_id = False
    else:
        file_id = str(max(photos['photo'], key=lambda x: x['width'])['file_id'])

    bot.nine_gag.update_item(
        Key={
            'postId': post_id
        },
        UpdateExpression="ADD viewed :user_id SET file_id = :file_id",
        ExpressionAttributeValues={
            ':user_id': {int(user_id)},
            ':file_id': file_id
        }
    )


def get_meme(bot: Leonard, user_id):
    meme = choice(bot.nine_gag.scan(
        FilterExpression=~Attr('viewed').contains(user_id)
    )['Items'])
    return meme['title'], \
           meme['img'] if 'file_id' not in meme or not meme['file_id'] else meme['file_id'], \
           meme['postId']