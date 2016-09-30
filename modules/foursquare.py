def register(bot):
    bot.handlers['foursquare-location-choice'] = location_choice


def location_choice(message, bot):
    bot.telegram.send_message(message.u_id, 'Hey there.')
    bot.call_handler(message, 'main-menu')
