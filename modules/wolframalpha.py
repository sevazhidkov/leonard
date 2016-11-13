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
    url = 'https://www.wolframalpha.com/input/?i=' + quote_plus(message.text)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Open on WolphramAlpha.com', url=url)]])
    res = list(response.results)
    exists = len(res) > 0
    if not exists:
        res = [x for x in response.pods if any(sub in x.title.lower() for sub in ('solution', 'root'))]
        exists = len(res) > 0
    plots = False
    if any('plot' in x.id.lower() for x in response.pods):
        plot = [x for x in response.pods if 'plot' in x.id.lower()]
        if not hasattr(plot[0], 'img') and hasattr(plot[0], 'subpod') and 'plot' in plot[0].title.lower():
            plot = list(plot[0].subpods)
        if plot and hasattr(plot[0], 'img'):
            plots = True
            bot.telegram.send_photo(
                message.u_id,
                photo=next(plot[0].img).src,
                reply_markup=reply_markup if not exists else None
            )
    if exists:
        if hasattr(res[0], 'img') and res[0].img is not None:
            bot.telegram.send_photo(message.u_id, photo=res[0].img, reply_markup=reply_markup)
        elif hasattr(res[0], 'text') and res[0].text is not None:
            bot.telegram.send_message(message.u_id, '\n'.join(list(map(lambda x: x.text, res))),
                                      reply_markup=reply_markup)
        else:
            bot.telegram.send_message(message.u_id, UNKNOWN_COMMAND, reply_markup=reply_markup)
    elif not plots:
        bot.telegram.send_message(message.u_id, UNKNOWN_COMMAND, reply_markup=reply_markup)
