import os
from redis import from_url


class Leonard:
    def __init__(self, telegram_client):
        self.telegram = telegram_client

        # Dict str -> function with all handlers for messages
        # and other updates
        self.handlers = {}

        self.redis = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    def handler(self, name):
        def decorator(func):
            def wrapper(message, bot):
                return func(message, bot)

            self.handlers[name] = wrapper
            return wrapper

        return decorator

    def process_message(self, message):
        pass
