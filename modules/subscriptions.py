import telegram
import jinja2

from leonard import Leonard
from modules import weather

INITIAL_WEATHER_OFFER = jinja2.Template("""You shouldn't write me to get help – you can subscribe to some notification messages.

⛅ Maybe weather? Morning forecasts or "Rain in next hour" reports?
""")
WEATHER_SETUP_RESULT = jinja2.Template(
    "👌 Not a problem, {% if result %}I subscribed you. It's ready " +
    "and will notificate you next time.{% else %}you can always change it later.{% endif %}"
)


def register(bot):
    bot.handlers['subscribes-setup'] = subscriptions_setup
    bot.handlers['subscribes-setup-result'] = subscriptions_setup_result
    bot.handlers['subscriptions-show'] = show_subscriptions
    bot.handlers['subscriptions-choose'] = choose_subscriptions
    bot.handlers['subscription-set'] = set_subscription


def subscriptions_setup(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'subscribes-setup-result')
    bot.telegram.send_message(
        chat_id=message.u_id,
        text=INITIAL_WEATHER_OFFER.render(),
        reply_markup=telegram.ReplyKeyboardMarkup(
            [['Yeah, send me morning forecasts 🌄'],
             ['Notificate me about upcoming rain ☔️'],
             ['No, thanks, I will setup it later 🚫']]
        )
    )


def subscriptions_setup_result(message, bot):
    base_key = 'notifications:{}:{}'.format(weather.NAME, '{}')
    if '🌄' in message.text:
        key = base_key.format('morning')
    elif '☔️' in message.text:
        key = base_key.format('rain')
    else:
        key = None
    bot.telegram.send_message(
        chat_id=message.u_id,
        text=WEATHER_SETUP_RESULT.render(result=key),
        reply_markup=telegram.ReplyKeyboardHide()
    )
    if key:
        bot.user_set(message.u_id, key, 1)
    bot.call_handler(message, 'welcome-location-setup')


def show_subscriptions(message, bot: Leonard):
    bot.user_set(message.u_id, 'next_handler', 'subscriptions-choose')
    reply_markup = telegram.ReplyKeyboardMarkup(
        [[telegram.KeyboardButton(subscription)] for subscription in bot.available_subscriptions.keys()]
    )
    bot.telegram.send_message(message.u_id, 'There are {} subscribe sources'.format(len(bot.available_subscriptions)),
                              reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)
    pass


def choose_subscriptions(message, bot: Leonard):
    if message.text in bot.available_subscriptions:
        bot.user_set(message.u_id, 'next_handler', 'subscription-set')
        chosen_subscriptions = bot.available_subscriptions[message.text]
        reply_markup = telegram.ReplyKeyboardMarkup(
            [[telegram.KeyboardButton('{} - {}'.format(message.text, subscription))] for subscription in
             chosen_subscriptions]
        )
        bot.telegram.send_message(message.u_id, 'There are {} subscription types'.format(len(chosen_subscriptions)),
                                  reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        bot.call_handler(message, 'main-menu')


def set_subscription(message, bot: Leonard):
    if len(message.text.split(' - ')) <= 1:
        bot.call_handler(message, 'main-menu')
        return
    plugin, subscription = message.text.split(' - ')
    if plugin not in bot.available_subscriptions:
        bot.call_handler(message, 'main-menu')
        return

    if subscription not in bot.available_subscriptions[plugin]:
        bot.call_handler(message, 'main-menu')
        return

    subscription = bot.available_subscriptions[plugin][subscription]
    bot.user_set(message.u_id, 'notifications:{}:{}'.format(plugin, subscription), 1)
    pass
