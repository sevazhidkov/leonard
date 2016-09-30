import os
import logging
import importlib

from flask import Flask
from redis import from_url

from telegram import Update
from telegram.message import Message

logger = logging.getLogger('leonard')


class Leonard:
    def __init__(self, telegram_client):
        self.default_handler = 'main-menu'

        self.telegram = telegram_client

        # Flask web app
        self.app = Flask(__name__)

        # Dict str -> function with all handlers for messages
        # and other updates
        self.handlers = {}

        self.redis = from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.bytes_fields = []

        self.logger = logger

    def collect_plugins(self):
        for plugin_name in os.listdir('modules'):
            if plugin_name.endswith('.py'):
                plugin = importlib.import_module('modules.{}'.format(plugin_name.rstrip('.py')))
                plugin.register(self)

    def process_update(self, update: Update):
        if update.message:
            self.process_message(update.message)

    def process_message(self, message: Message):
        # Add snippets
        message.u_id = message.from_user.id
        message.moved = False

        current_handler = self.user_get(message.u_id, 'next_handler') or self.default_handler
        self.user_set(message.u_id, 'handler', current_handler)
        self.user_set(message.u_id, 'next_handler', '')

        self.handlers[current_handler](message, self)

    def call_handler(self, message, name):
        self.user_set(message.u_id, 'handler', name)
        message.moved = True
        self.handlers[name](message, self)

    def user_get(self, user_id, field, default=None):
        key = 'user:{}:{}'.format(user_id, field)
        value = self.redis.get(key) or default
        if type(value) == bytes and field not in self.bytes_fields:
            value = value.decode('utf-8')
        logger.info('redis get {} => {}'.format(key, value))
        return value

    def user_set(self, user_id, field, value):
        key = 'user:{}:{}'.format(user_id, field)
        self.redis.set(key, value)
        logger.info('redis set {} => {}'.format(key, value))
