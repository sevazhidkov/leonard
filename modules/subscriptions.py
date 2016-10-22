import telegram
import jinja2

from leonard import Leonard

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
    base_key = 'notifications:weather:{}'
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
