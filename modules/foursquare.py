import os
import json
import jinja2
import telegram
import foursquare

from modules.location import reverse_geocode

SEND_YOUR_LOCATION = ("Find a cool place using Foursquare data isn't problem for me 👌\n\n"
                      "🌏 Where are you? You can use your default location")
SEND_YOUR_QUERY = ("Cool 👍 Tell me, where do you want to go? ☕ 🍝 🍟\n\n"
                   "Like \"dance club\", \"quiet place\" or \"big moll\". "
                   "Otherwise you can use one of categories below 👇")
NOT_FOUND = "I'm sorry, but there is nothing to show you for now 😁"
SEARCH_RESULT = jinja2.Template("{{ venue.name }}\n\n{% if venue.rating %}{{'⭐️' * venue.rating}}{% endif %}")

CATEGORY_EMOJI = {
    'Café': '🍝'
}
FOURSQUARE_LINK = 'https://foursquare.com/v/{}'

client = foursquare.Foursquare(client_id=os.environ['FOURSQUARE_CLIENT_ID'],
                               client_secret=os.environ['FOURSQUARE_CLIENT_SECRET'])


def register(bot):
    bot.handlers['foursquare-location-choice'] = location_choice
    bot.handlers['foursquare-query-choice'] = query_choice
    bot.handlers['foursquare-search-results'] = search_results

    bot.callback_handlers['foursquare-previous'] = previous_result_callback
    bot.callback_handlers['foursquare-next'] = next_result_callback


def location_choice(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'foursquare-query-choice')
    base_location_name = json.loads(bot.user_get(message.u_id, 'location'))['full_name']
    keyboard = [[telegram.KeyboardButton('📍 Send current location', request_location=True)],
                [telegram.KeyboardButton('🏠 ' + base_location_name)]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    bot.telegram.send_message(message.u_id, SEND_YOUR_LOCATION, reply_markup=reply_markup)


def query_choice(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'foursquare-search-results')
    if message.location:
        bot.user_set(
            message.u_id, 'foursquare:location',
            json.dumps(
                reverse_geocode(message.location['latitude'], message.location['longitude'], bot)
            )
        )
    else:
        bot.user_set(message.u_id, 'foursquare:location', bot.user_get(message.u_id, 'location'))
    bot.telegram.send_message(message.u_id, SEND_YOUR_QUERY)


def search_results(message, bot):
    query = message.text
    location = json.loads(bot.user_get(message.u_id, 'location'))
    response = client.venues.explore(
        params={'query': query, 'll': '{},{}'.format(location['lat'], location['long'])}
    )
    bot.logger.info('Foursquare answer: {}'.format(response))

    results = []
    for item in response['groups'][0]['items']:
        venue = {}

        if item['venue']['categories']:
            category_name = item['venue']['categories'][0]['name']
            template = category_name + ' «{}»'
            if category_name in CATEGORY_EMOJI:
                template += ' ' + CATEGORY_EMOJI[category_name]
        else:
            template = '«{}»'

        venue['name'] = template.format(item['venue']['name'])
        venue['reasons'] = [reason['summary'] for reason in item['reasons']['items']]
        venue['url'] = FOURSQUARE_LINK.format(item['venue']['id'])

        venue['rating'] = 0
        if 'rating' in item['venue']:
            venue['rating'] = round_rating(item['venue']['rating'])
        results.append(venue)

    bot.user_set(message.u_id, 'foursquare:results', json.dumps(results))
    bot.user_set(message.u_id, 'foursquare:results:current', 0)

    if not results:
        bot.telegram.send_message(message.u_id, NOT_FOUND)
        return
    reply_markup = build_result_keyboard(results[0], 0, len(results) - 1)
    bot.telegram.send_message(message.u_id, SEARCH_RESULT.render(
        venue=results[0]
    ), reply_markup=reply_markup)


def previous_result_callback(query, bot):
    results = json.loads(bot.user_get(query.u_id, 'foursquare:results'))

    cur_result = bot.user_get(query.u_id, 'foursquare:results:current')
    if cur_result - 1 < 0:
        return
    cur_result -= 1
    bot.user_set(query.u_id, 'foursquare:results:current', cur_result)

    venue = results[cur_result]
    edit_current_result(venue, cur_result, query, results, bot)


def next_result_callback(query, bot):
    results = json.loads(bot.user_get(query.u_id, 'foursquare:results'))

    cur_result = bot.user_get(query.u_id, 'foursquare:results:current')
    if cur_result + 1 >= len(results):
        return
    cur_result += 1
    bot.user_set(query.u_id, 'foursquare:results:current', cur_result)

    venue = results[cur_result]
    edit_current_result(venue, cur_result, query, results, bot)


def edit_current_result(venue, cur_result, query, results, bot):
    bot.telegram.editMessageText(
        text=SEARCH_RESULT.format(venue=venue),
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=build_result_keyboard(venue, cur_result, len(results) - 1),
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


def round_rating(value):
    if value - int(value) >= 0.5:
        return int(value) + 1
    else:
        return int(value)


def build_result_keyboard(venue, num=0, last_num=1):
    back_button = telegram.InlineKeyboardButton('⏮ Back', callback_data='foursquare-previous')
    next_button = telegram.InlineKeyboardButton('Next ⏭', callback_data='foursquare-next')
    keyboard = [[],
                [telegram.InlineKeyboardButton('Get location 📍', callback_data='foursquare-get-location')],
                [telegram.InlineKeyboardButton('Open on Foursquare 🌐', url=venue['url'])]]
    if num != 0:
        keyboard[0].append(back_button)
    if num != last_num:
        keyboard[0].append(next_button)
    return telegram.InlineKeyboardMarkup(keyboard)