import io
from PIL import Image, ImageOps
from bs4 import BeautifulSoup
import wikipedia
import jinja2
import telegram
import requests

from libs.imageutils import fit_size

ARTICLE = jinja2.Template("*{{title}}*\n{{article}}")


def register(bot):
    bot.handlers["wiki-search"] = search
    bot.handlers["wiki-make-query"] = make_query


def search(message, bot):
    bot.send_message(message.u_id, 'What do you want to know? 🤓')
    bot.user_set(message.u_id, 'next_handler', 'wiki-make-query')


def select_sentences(text, sentences):
    result_text = ""
    sentences_count = 0
    for ch in text:
        if sentences_count == sentences: break
        if ch == ".": sentences_count += 1
        result_text += ch
    return result_text


def make_query(message, bot):
    try:
        results = wikipedia.search(message.text)
    except requests.exceptions.InvalidURL:
        results = False
    if results:
        try:
            article = wikipedia.page(results[0])
            inbox = BeautifulSoup(article.html(), "lxml").find("table", attrs={"class":["infobox vcard", "infobox geography vcard"]})
            summary = select_sentences(article.summary, 4)[:400]
            title = article.title

            if 'may refer to' in summary:
                raise wikipedia.DisambiguationError(may_refer_to=results[1:], title=title)

            url = article.url
            keyboard = build_result_keyboard(url)

            if inbox:
                image = inbox.find("img")
                if image and int(image["width"])>20:
                    image = "https:"+image["src"]
                    try:
                        bot.telegram.send_photo(message.u_id, photo=image)
                    except Exception:
                        bot.telegram.send_photo(
                            message.u_id,
                            photo=fit_size(image)
                        )

            bot.send_message(message.u_id,
                             ARTICLE.render(title=title, article=summary),
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=keyboard)

            bot.send_message(message.u_id, 'What do you want to know else? 🤓')

        except wikipedia.DisambiguationError as ex:
            keyboard = telegram.ReplyKeyboardMarkup(
                [[result] for result in ex.options[: 4 if len(ex.options) - 4 else -1]] + [["Back to the menu 🏠"]])
            bot.send_message(message.u_id, 'This word has many meanings, select one 📔', reply_markup=keyboard)
    else:
        bot.send_message(message.u_id, "I'm sorry, I didn't find anything ☹️")
        bot.send_message(message.u_id, 'What do you want to know else? 🤓')
    bot.user_set(message.u_id, 'next_handler', 'wiki-make-query')

def build_result_keyboard(article_url):
    url_button = telegram.InlineKeyboardButton("Open article 🌐", url=article_url)
    keyboard = [[url_button]]
    return telegram.InlineKeyboardMarkup(keyboard)
