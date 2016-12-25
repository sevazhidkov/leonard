from wikiapi import WikiApi
import jinja2
import telegram

wiki = WikiApi({ 'locale' : 'en'})
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
        if ch == ".": sentences_count+=1
        result_text+=ch
    return result_text

def make_query(message, bot):
    results = wiki.find(message.text)
    if results:
        article = wiki.get_article(results[0])
        if "may refer to" in article.summary:
            if len(results)>1: article = wiki.get_article(results[1])
            else: bot.send_message(message.u_id, "I'm sorry, I didn't find anything ☹️")
        summary = select_sentences(article.summary, 4)
        title = article.heading
        url = article.url
        keyboard = build_result_keyboard(url)

        if article.image: bot.telegram.send_photo(message.u_id, photo=article.image)

        bot.send_message(message.u_id, ARTICLE.render(title = title,
                                                      article = summary),
                                                      parse_mode=telegram.ParseMode.MARKDOWN,
                                                      reply_markup=keyboard)
    else:
        bot.send_message(message.u_id, "I'm sorry, I didn't find anything ☹️")
    bot.user_set(message.u_id, 'next_handler', 'wiki-make-query')
    bot.send_message(message.u_id, 'What do you want to know else? 🤓')

def build_result_keyboard(article_url):
    url_button = telegram.InlineKeyboardButton("Open article 🌐", url=article_url)
    keyboard = [[url_button]]
    return telegram.InlineKeyboardMarkup(keyboard)
