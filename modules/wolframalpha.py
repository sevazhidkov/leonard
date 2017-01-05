import os

import io
import requests
import wolframalpha
from PIL import Image, ImageOps

from leonard import Leonard
from libs.imageutils import fit_size

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
            for subpod in pod.subpod:
                for img in subpod.img:
                    link = None
                    try:
                        link = img.src
                        bot.telegram.send_photo(
                            message.u_id,
                            photo=link,
                            caption=pod.title
                        )
                    except Exception:
                        bot.telegram.send_photo(
                            message.u_id,
                            photo=fit_size(link),
                            caption=pod.title
                        )
                        continue
        for result in response.results:
            bot.telegram.send_message(
                message.u_id,
                text=result.text
            )
    else:
        bot.telegram.send_message(message.u_id, UNKNOWN_COMMAND)



    bot.user_set(message.u_id, 'next_handler', 'wolfram-result')
    bot.send_message(message.u_id, 'What do you want to calculate or know else? 🤔')
