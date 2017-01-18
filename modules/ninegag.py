import collections
import json
from random import choice

import pytz
import boto3
from boto3.dynamodb.conditions import Attr, AttributeNotExists
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import jinja2

from leonard import Leonard
from libs.timezone import local_time

DAILY_MEME_HOURS = [10, 11, 12]

dynamo = boto3.resource('dynamodb', 'eu-west-1')

def sort_by_points(meme):
    if "points" in meme:
        return meme["points"]
    else:
        return 0

def register(bot):
    bot.nine_gag = dynamo.Table('LeonardBot9gagPosts')

    bot.handlers['meme-show'] = show_meme

    bot.subscriptions.append({'name': 'daily-meme', 'check': daily_meme_check,
                              'send': daily_meme_send})


def daily_meme_check(bot: Leonard):
    result = []

    for key in bot.redis.scan_iter(match='user:*:notifications:9gag:daily-meme'):
        key = key.decode('utf-8')
        status = bot.redis.get(key).decode('utf-8')
        sent = bot.redis.get(key + ':sent')
        if status != '1' or (sent and sent.decode('utf-8') == '1'):
            continue
        _, user_id, _, _, _ = key.split(':')

        if not bot.user_get(user_id, "location"): continue

        time = local_time(bot, int(user_id))

        if time and time.hour in DAILY_MEME_HOURS:
            result.append(int(user_id))

    return result


def daily_meme_send(bot: Leonard, users):
    for u_id in users:
        try:
            key = 'user:{}:notifications:9gag:daily-meme:sent'.format(u_id)
            bot.redis.set(key, '1', ex=(len(DAILY_MEME_HOURS) + 1) * 60 * 60)
            bot.telegram.send_message(u_id, 'Here is your daily meme, my friend! 😆')
            show_meme(None, bot, u_id)
        except Exception as error:
            bot.logger.error(error)


def show_meme(message, bot: Leonard, user_id=None):
    if message:
        user_id = message.u_id
    meme, title, img, post_id, points = get_meme(bot, user_id)
    try:
        photos = bot.telegram.send_photo(
            user_id,
            photo=img,
            caption=title,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Open on 9GAG', url='9gag.com/gag/' + post_id)]])
        )
    except Exception:
        pass
    if bot.debug:
        file_id = False if 'file_id' not in meme or not meme['file_id'] else meme['file_id']
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
    meme = sorted(bot.nine_gag.scan(
        FilterExpression=~Attr('viewed').contains(user_id)
    )['Items'], key = sort_by_points)[-1]
    return meme, meme.get('title', ''), \
           meme['img'] if 'file_id' not in meme or not meme['file_id'] else meme['file_id'], \
           meme['postId'], \
           meme["points"] if "points" in meme else 0
