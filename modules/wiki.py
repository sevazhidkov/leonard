from wikiapi import WikiApi
import jinja2
import telegram

wiki = WikiApi({ 'locale' : 'en'})
ARTICLE = jinja2.Template("*{{title}}*\n{{article}}")

def register(bot):
    bot.handlers["wiki-search"] = search
    bot.handlers["wiki-make-query"] = make_query
    bot.callback_handlers["wiki-other-meanings"] = other_meanings


def search(message, bot):
    bot.send_message(message.u_id, 'What do you want to know? 🤓')
    bot.user_set(message.u_id, 'next_handler', 'wiki-make-query')


def select_sentences(text, sentences):
    result_text = ""
    sentences_count = 0
    for ch in text:
        if sentences_count == sentences: break
        if ch == ".": sentences_count+=1
        result_text+=ch
    return result_text

def make_query(message, bot):
    results = wiki.find(message.text)
    if results:
        article = wiki.get_article(results[0])
        meanings_word = ""
        if "may refer to" in article.summary:
            if len(results)>1:
                article = wiki.get_article(results[1])
                meanings_word = message.text
            else: bot.send_message(message.u_id, "I'm sorry, I didn't find anything ☹️")
        summary = select_sentences(article.summary, 4)
        title = article.heading
        url = article.url
        keyboard = build_result_keyboard(url, meanings_word)

        if article.image: bot.telegram.send_photo(message.u_id, photo=article.image)

        bot.send_message(message.u_id, ARTICLE.render(title = title,
                                                      article = summary),
                                                      parse_mode=telegram.ParseMode.MARKDOWN,
                                                      reply_markup=keyboard)
    else:
        bot.send_message(message.u_id, "I'm sorry, I didn't find anything ☹️")
    bot.user_set(message.u_id, 'next_handler', 'wiki-make-query')
    bot.send_message(message.u_id, 'What do you want to know else? 🤓')

def other_meanings(query, bot):
    user_query = query.data.split("/")[1]
    results = wiki.find(user_query)[1:]
    keyboard = telegram.ReplyKeyboardMarkup([[result.replace("_"," ").replace("%26"," ")] for result in results]+[["Back to the menu 🏠"]])
    bot.send_message(query.u_id, 'What do you want to know else? 🤓',reply_markup=keyboard)
    bot.user_set(query.u_id, 'next_handler', 'wiki-make-query')

def build_result_keyboard(article_url, word):
    url_button = telegram.InlineKeyboardButton("Open article 🌐", url=article_url)
    meanings_word_button = telegram.InlineKeyboardButton("Other meanings of the \"%s\""%word, callback_data="wiki-other-meanings/%s"%word)
    keyboard = [[url_button]]
    if word: keyboard.append([meanings_word_button])
    return telegram.InlineKeyboardMarkup(keyboard)
