import jinja2

WELCOME_LOCATION_SETUP = ""


def register(bot):
    bot.handlers['welcome-location-setup'] = welcome_location_setup


def welcome_location_setup(message, bot):
    pass
