import os
from urllib.parse import quote_plus

import jinja2
import wolframalpha
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from leonard import Leonard

UNKNOWN_COMMAND = 'Wolfram Alpha doesn\'t know anything about that 😢'


def register(bot):
    bot.wolfram_client = wolframalpha.Client(os.environ['WOLPHRAM_ALPHA_KEY'])
    bot.handlers['wolfram-ask'] = ask_wolfram
    bot.handlers['wolfram-result'] = wolfram_result


def ask_wolfram(message, bot: Leonard):
    bot.user_set(message.u_id, 'next_handler', 'wolfram-result')
    bot.send_message(message.u_id, 'What do you want to calculate or know about? 🤔')


def wolfram_result(message, bot: Leonard):
    bot.telegram.send_message(message.u_id, 'Wolfram Alpha is thinking... ⌛️',
                              reply_markup=bot.get_menu(message))
    if not message.text:
        bot.telegram.send_message(message.u_id, UNKNOWN_COMMAND)
        return
    response = bot.wolfram_client.query(message.text)
    bot.logger.info('Wolfram Alpha response: "{}" for query "{}"'.format(response, message.text))
    if not hasattr(response, 'pods'):
        bot.telegram.send_message(message.u_id, UNKNOWN_COMMAND)
        return
    pods = list(response.pods)
    exists = len(pods)
    if exists:
        for pod in pods[:-1]:
            bot.telegram.send_photo(
                message.u_id,
                photo=next(next(pod.subpod).img).src,
                caption=pod.title
            )
    else:
        bot.telegram.send_message(message.u_id, UNKNOWN_COMMAND)

    bot.user_set(message.u_id, 'next_handler', 'wolfram-result')
<<<<<<< HEAD
    bot.send_message(message.u_id, 'What do you want to calculate or know else? 🤔')
=======
    bot.send_message(message.u_id, 'What do you want to calculate or know else? 🤓')
>>>>>>> 0b11ffe89fe85acbfb809a712f45a819aa14320b
