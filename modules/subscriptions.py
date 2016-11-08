import telegram
import jinja2

from leonard import Leonard
from modules import weather

SUBSCRIBES_MENU = [[{'plugin': 'weather', 'name': 'morning-forecast', 'text': 'Morning weather 🌅',
                     'on_add': 'Yay! Next morning I\'ll send you forecast 👌'}],
                   [{'plugin': 'weather', 'name': 'rain-notifications', 'text': 'Before rain ☔'},
                    {'plugin': '9gag', 'name': 'daily-meme', 'text': 'Daily meme 😅'}],
                   [{'plugin': 'news', 'name': 'news-digest', 'text': 'News digest 📰',
                    'on_add': 'Cool! I will send you news next evening 👌'}]]

DEFAULT_SUBSCRIBE_TEXT = 'Cool! I will write you next time.'
DEFAULT_UNSUBSCRIBE_TEXT = 'Sorry 😁'

INITIAL_WEATHER_OFFER = jinja2.Template("""You shouldn't write me to get help – you can subscribe to some notification messages.

⛅ Maybe weather? Morning forecasts or notifications about rain?
""")
WEATHER_SETUP_RESULT = jinja2.Template(
    "👌 Not a problem, {% if result %}I subscribed you. It's ready " +
    "and will notificate you next time.{% else %}you can always change it later.{% endif %}"
)


def register(bot: Leonard):
    bot.handlers['subscriptions-setup'] = subscriptions_setup
    bot.handlers['subscriptions-setup-result'] = subscriptions_setup_result
    bot.handlers['subscriptions-show'] = show_subscriptions
    bot.handlers['subscription-set'] = set_subscription


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
    base_key = 'notifications:{}:{}'.format(weather.NAME, '{}')
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
    bot.user_set(message.u_id, 'next_handler', 'subscription-set')
    keyboard = build_subscribes_keyboard(message, bot)
    bot.telegram.send_message(
        message.u_id,
        "I can send you periodical messages about something happens around you.\n\n"
        "Look what I can offer you. 🙂",
        reply_markup=telegram.ReplyKeyboardMarkup(keyboard)
    )


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
    current_status = bot.user_get(message.u_id, key)
    if current_status == '1':
        bot.user_set(message.u_id, key, '')
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
            row_status = bot.user_get(message.u_id, 'notifications:{}:{}'.format(row['plugin'], row['name']))
            if row_status == '1':
                status_emoji = '✅'
            else:
                status_emoji = '❌'
            subkeyboard.append(status_emoji + ' ' + row['text'])
        if subkeyboard:
            keyboard.append(subkeyboard)
    keyboard.append([bot.MENU_BUTTON])
    return keyboard
