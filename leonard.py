import os
import importlib
from redis import from_url
from telegram import Update
from telegram.message import Message


class Leonard:
    def __init__(self, telegram_client):
        self.default_handler = 'welcome-message'
        self.menu_handler = 'menu'

        self.telegram = telegram_client

        # Dict str -> function with all handlers for messages
        # and other updates
        self.handlers = {}

        self.redis = from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

    def collect_plugins(self):
        for plugin_name in os.listdir('modules'):
            if plugin_name.endswith('.py'):
                plugin = importlib.import_module('modules.{}'.format(plugin_name.rstrip('.py')))
                plugin.register(self)

    def process_update(self, update: Update):
        if update.message:
            self.process_message(update.message)

    def process_message(self, message: Message):
        current_handler = self.user_get(message.from_user.id, 'handler',
                                        default=self.default_handler)

        self.handlers[current_handler](message, self)

    def user_get(self, user_id, field, default=None):
        key = 'user:{}:{}'.format(user_id, field)
        value = self.redis.get(key) or default
        return value
