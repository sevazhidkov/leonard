import os
import json
from geopy.distance import vincenty as _distance

import jinja2
import telegram
import foursquare

from modules.location import set_location

SEND_YOUR_LOCATION = "🌏 Where are you? You can use your default location"
SEND_YOUR_QUERY = ("Cool 👍 Tell me, where do you want to go? ☕ 🍝 🍟\n\n"
                   "You can send your own query or use one of our variants 👇")
NOT_FOUND = "I'm sorry, but there is nothing to show you for now 😁"
WAIT_A_SECOND = 'Wait a second, please, I\'m searching cool venue on the Foursquare 🕐'
SEARCH_RESULT = jinja2.Template("*{{ venue.name }}*"
                                "{% if venue.location.address %}, _{{ venue.location.address }}_{% endif %}\n"
                                "*{{distance}} to you*\n\n"
                                "{% for reason in venue.reasons %}— {{ reason }}{% endfor %}\n\n"
                                "{% if venue.rating %}{{'⭐️' * venue.rating}}\n"
                                "{% endif %}{{ '💲' * venue.price_tier }}\n\n"
                                "{{ venue.url }}")

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
    bot.callback_handlers['foursquare-get-location'] = get_location_callback
    bot.callback_handlers['foursquare-get-uber'] = get_uber


def location_choice(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'foursquare-query-choice')
    base_location_name = json.loads(bot.user_get(message.u_id, 'location'))['full_name']
    keyboard = [[telegram.KeyboardButton('📍 Send current location', request_location=True)],
                [telegram.KeyboardButton('🏠 ' + base_location_name)],
                [bot.MENU_BUTTON]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    bot.telegram.send_message(message.u_id, SEND_YOUR_LOCATION, reply_markup=reply_markup)


def query_choice(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'foursquare-search-results')
    if message.location:
        set_location(bot, message.u_id, message.location)

    bot.user_set(message.u_id, 'foursquare:location', bot.user_get(message.u_id, 'location'))
    keyboard = telegram.ReplyKeyboardMarkup([['Coffee ☕', 'Restaurant 🍴'],
                                             ['Pizza 🍕', 'Club 🎤'],
                                             ['Shop 🛍', 'Chinese 🍝'],
                                             [bot.MENU_BUTTON]])
    bot.telegram.send_message(message.u_id, SEND_YOUR_QUERY, reply_markup=keyboard)


def search_results(message, bot):
    bot.telegram.send_message(message.u_id, WAIT_A_SECOND, reply_markup=bot.get_menu(message))
    query = message.text
    location = json.loads(bot.user_get(message.u_id, 'location'))
    response = client.venues.explore(
        params={'query': query, 'll': '{},{}'.format(location['lat'], location['long'])}
    )

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

        print(item['venue'])

        venue['name'] = template.format(item['venue']['name'])
        venue['reasons'] = [reason['summary'] for reason in item['reasons']['items']]
        venue['url'] = FOURSQUARE_LINK.format(item['venue']['id'])
        try:
            venue['price_tier'] = item['venue']['price']['tier']
        except KeyError:
            venue['price_tier'] = 2

        bot.logger.info(item['venue']['location'])

        venue['location'] = {
            'lat': item['venue']['location']['lat'],
            'long': item['venue']['location']['lng'],
            'address': item['venue']['location'].get('address', '')
        }
        distance = _distance(
            (venue['location']['lat'], venue['location']['long']),
            (location['lat'], location['long'])
        )
        venue['km'] = round(distance.km, 1)
        venue['m'] = round(distance.m)

        venue['rating'] = 0
        if 'rating' in item['venue']:
            venue['rating'] = round_rating(item['venue']['rating'])
        else:
            venue['rating'] = 3
        results.append(venue)

    bot.user_set(message.u_id, 'foursquare:results', json.dumps(results))
    bot.user_set(message.u_id, 'foursquare:results:current', 0)

    if not results:
        bot.telegram.send_message(message.u_id, NOT_FOUND)
        bot.call_handler(message, 'main-menu')
        return
    reply_markup = build_result_keyboard(results[0], 0, len(results) - 1)
    bot.telegram.send_message(
        message.u_id,
        SEARCH_RESULT.render(
            venue=results[0],
            distance = '{}m'.format(venue['m']) if venue['km'] < 1 else '{}km'.format(venue['km'])
        ),
        reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


def get_location_callback(query, bot):
    results = json.loads(bot.user_get(query.u_id, 'foursquare:results'))
    cur_result = int(bot.user_get(query.u_id, 'foursquare:results:current'))
    venue = results[cur_result]

    # Delete inline keyboard from Foursquare card
    try:
        bot.telegram.editMessageReplyMarkup(
            reply_markup=telegram.InlineKeyboardMarkup([]),
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            disable_web_page_preview=True
        )
    except telegram.error.BadRequest:
        pass
    bot.telegram.send_location(
        chat_id=query.message.chat_id,
        longitude=venue['location']['long'],
        latitude=venue['location']['lat']
    )

    reply_markup = build_result_keyboard(results[cur_result], cur_result, len(results) - 1)
    bot.telegram.send_message(
        query.u_id,
        SEARCH_RESULT.render(venue=results[cur_result],
                            distance = '{}m'.format(venue['m']) if venue['km'] < 1 else '{}km'.format(venue['km'])),
        reply_markup=reply_markup,
        parse_mode=telegram.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


def previous_result_callback(query, bot):
    results = json.loads(bot.user_get(query.u_id, 'foursquare:results'))

    cur_result = int(bot.user_get(query.u_id, 'foursquare:results:current'))
    if cur_result - 1 < 0:
        return
    cur_result -= 1
    bot.user_set(query.u_id, 'foursquare:results:current', cur_result)

    venue = results[cur_result]
    edit_current_result(venue, cur_result, query, results, bot)


def next_result_callback(query, bot):
    results = json.loads(bot.user_get(query.u_id, 'foursquare:results'))

    cur_result = int(bot.user_get(query.u_id, 'foursquare:results:current'))
    if cur_result + 1 >= len(results):
        return
    cur_result += 1
    bot.user_set(query.u_id, 'foursquare:results:current', cur_result)

    venue = results[cur_result]
    edit_current_result(venue, cur_result, query, results, bot)


def edit_current_result(venue, cur_result, query, results, bot):
    bot.telegram.editMessageText(
        text=SEARCH_RESULT.render(venue=venue,
                                 distance = '{}m'.format(venue['m']) if venue['km'] < 1 else '{}km'.format(venue['km'])),
        parse_mode=telegram.ParseMode.MARKDOWN,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        disable_web_page_preview=True
    )
    bot.telegram.editMessageReplyMarkup(
        reply_markup=build_result_keyboard(venue, cur_result, len(results) - 1),
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


def round_rating(value):
    value = value / 10 * 5
    if value - int(value) >= 0.5:
        return int(value) + 1
    else:
        return int(value)

def get_uber(query, bot):
    if bot.user_get(query.u_id, 'uber:authorized') != '1':
        bot.call_handler(query, 'uber-oauth-start')

def build_result_keyboard(venue, num=0, last_num=1):
    back_button = telegram.InlineKeyboardButton('⏮ Back', callback_data='foursquare-previous')
    next_button = telegram.InlineKeyboardButton('Next ⏭', callback_data='foursquare-next')
    keyboard = [[],
                [telegram.InlineKeyboardButton('Show location 📍', callback_data='foursquare-get-location'),
                telegram.InlineKeyboardButton('Get Uber 🚘 ', callback_data='uber-inline')],
                [telegram.InlineKeyboardButton('Open on Foursquare 🌐', url=venue['url'])]]
    if num != 0:
        keyboard[0].append(back_button)
    if num != last_num:
        keyboard[0].append(next_button)
    return telegram.InlineKeyboardMarkup(keyboard)
