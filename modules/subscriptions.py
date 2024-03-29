import telegram
import jinja2

from leonard import Leonard

SUBSCRIBES_MENU = [[{'plugin': 'weather', 'name': 'morning-forecast', 'text': 'Morning weather 🌅',
                     'on_add': 'Yay! Next morning I\'ll send you forecast 👌'}],
                   [{'plugin': 'weather', 'name': 'rain-notifications', 'text': 'Before rain ☔'},
                    {'plugin': '9gag', 'name': 'daily-meme', 'text': 'Daily meme 😅'}],
                   [{'plugin': 'news', 'name': 'news-digest', 'text': 'News digest 📰',
                    'on_add': 'Cool! I will send you news next evening 👌'},
                    {'plugin': 'producthunt', 'name': 'daily-hunt', 'text': 'Product Hunt 🔥',
                     'on_add': 'Cool! I will send you news next evening 👌'}],
                    [{'plugin': 'returns', 'name': 'messages', 'text': 'Reminders about bot 🤖',
                     'default': '1'}]]

DEFAULT_SUBSCRIBE_TEXT = 'Cool! I will write you next time.'
DEFAULT_UNSUBSCRIBE_TEXT = 'Sorry 😁'

INITIAL_WEATHER_OFFER = jinja2.Template("""Can I send you everyday morning forecast ⛅ ? Or maybe notifications before rain? ☔""")
WEATHER_SETUP_RESULT = jinja2.Template(
    "{% if result %} That's cool, I won't let you down 👌 {% else %}"
    "Not a problem, you can always change it later 🤔{% endif %}"
)


def register(bot: Leonard):
    bot.handlers['subscriptions-setup'] = subscriptions_setup
    bot.handlers['subscriptions-setup-result'] = subscriptions_setup_result
    bot.handlers['subscriptions-show'] = show_subscriptions
    bot.handlers['subscription-set'] = set_subscription

    bot.callback_subscriptions['9gag-subscribe'] = (set_subscription_by_name, [y for x in SUBSCRIBES_MENU for y in x if y['plugin'] == '9gag'][0])


# REGISTRATION HANDLERS


def subscriptions_setup(message, bot: Leonard):
    bot.user_set(message.u_id, 'next_handler', 'subscriptions-setup-result')
    bot.telegram.send_message(
        chat_id=message.u_id,
        text=INITIAL_WEATHER_OFFER.render(),
        reply_markup=telegram.ReplyKeyboardMarkup(
            [['Yeah, send me morning forecasts 🌄'],
             ['Notificate me about upcoming rain ☔️'],
             ['No, thanks, I will setup it later 🚫']]
        )
    )


def subscriptions_setup_result(message, bot: Leonard):
    base_key = 'notifications:weather:{}'
    if '🌄' in message.text:
        key = base_key.format('morning-forecast')
    elif '☔️' in message.text:
        key = base_key.format('rain-notifications')
    else:
        key = None
    bot.telegram.send_message(
        chat_id=message.u_id,
        text=WEATHER_SETUP_RESULT.render(result=key),
        reply_markup=telegram.ReplyKeyboardHide()
    )
    if key:
        bot.user_set(message.u_id, key, 1)
        bot.redis.expire('user:{}:{}'.format(message.u_id, key), 24 * 60 * 60)
    bot.call_handler(message, 'welcome-location-setup')


# SUBSCRIPTIONS MENU HANDLERS


def show_subscriptions(message, bot: Leonard):
    keyboard = build_subscribes_keyboard(message, bot)
    bot.telegram.send_message(
        message.u_id,
        "I can send you periodical messages about something happens around you.\n\n"
        "Look what I can offer you. 🙂",
        reply_markup=telegram.ReplyKeyboardMarkup(keyboard)
    )
    bot.user_set(message.u_id, 'next_handler', 'subscription-set')

def set_subscription_by_name(active_subscription, query, bot: Leonard):
    key = 'notifications:{}:{}'.format(active_subscription['plugin'], active_subscription['name'])
    bot.user_set(query.u_id, key, '1')
    reply_text = active_subscription.get('on_add', DEFAULT_SUBSCRIBE_TEXT)
    bot.telegram.send_message(query.u_id, reply_text)
    bot.telegram.editMessageReplyMarkup(chat_id=query.message.chat_id, message_id=query.message.message_id, reply_markup=None)

def set_subscription(message, bot: Leonard):
    bot.user_set(message.u_id, 'next_handler', 'subscription-set')
    active_subscription = None
    for line in SUBSCRIBES_MENU:
        for row in line:
            if row['text'] in message.text:
                active_subscription = row
                break
        if active_subscription:
            break
    else:
        bot.call_handler(message, 'subscriptions-show')
        return

    key = 'notifications:{}:{}'.format(active_subscription['plugin'], active_subscription['name'])
    default_status = None
    if 'default' in active_subscription:
        default_status = active_subscription['default']
    current_status = bot.user_get(message.u_id, key) or default_status
    if current_status == '1':
        bot.user_set(message.u_id, key, '0')
        reply_text = active_subscription.get('on_delete', DEFAULT_UNSUBSCRIBE_TEXT)
    else:
        bot.user_set(message.u_id, key, '1')
        reply_text = active_subscription.get('on_add', DEFAULT_SUBSCRIBE_TEXT)
    bot.telegram.send_message(
        message.u_id, reply_text,
        reply_markup=telegram.ReplyKeyboardMarkup(build_subscribes_keyboard(message, bot))
    )


def build_subscribes_keyboard(message, bot):
    keyboard = []
    for line in SUBSCRIBES_MENU:
        subkeyboard = []
        for row in line:
            default_status = None
            if 'default' in row:
                default_status = row['default']
            row_status = bot.user_get(
                message.u_id, 'notifications:{}:{}'.format(row['plugin'], row['name'])
            ) or default_status
            if row_status == '1':
                status_emoji = '✅'
            else:
                status_emoji = '❌'
            subkeyboard.append(status_emoji + ' ' + row['text'])
        if subkeyboard:
            keyboard.append(subkeyboard)
    keyboard.append([bot.MENU_BUTTON])
    return keyboard
