import os
import logging
import importlib

import boto3
import collections
from flask import Flask
from redis import from_url

from telegram import Update, ReplyKeyboardMarkup
from telegram.message import Message
from tzwhere import tzwhere

logger = logging.getLogger('leonard')


class Leonard:
    def __init__(self, telegram_client, debug=False):
        self.MENU_BUTTON = 'Back to the menu 🏠'

        self.debug = debug
        self.default_handler = 'main-menu'

        self.telegram = telegram_client

        # Flask web app
        self.app = Flask(__name__)

        # Dict str -> function with all handlers for messages
        # and other updates
        self.handlers = {}
        self.callback_handlers = {}

        self.redis = from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.bytes_fields = []

        self.logger = logger

        self.subscriptions = []
        self.available_subscriptions = {}
        self.tz = tzwhere.tzwhere()

        self.dynamo = boto3.resource('dynamodb', 'eu-central-1')
        self.nine_gag = self.dynamo.Table('9gag')

    def collect_plugins(self):
        for plugin_name in os.listdir('modules'):
            if plugin_name.endswith('.py'):
                plugin = importlib.import_module('modules.{}'.format(plugin_name.rstrip('.py')))
                if hasattr(plugin, 'SUBSCRIBES'):
                    self.available_subscriptions[
                        plugin.NAME if hasattr(plugin, 'NAME') else plugin_name.rstrip('.py')
                    ] = (plugin.ORDER, plugin.SUBSCRIBES)
                plugin.register(self)
        self.available_subscriptions = collections.OrderedDict([(x, y[1]) for x, y in sorted(self.available_subscriptions.items(), key=lambda x: x[1][0])])

    def send_message(self, *args, **kwargs):
        if 'reply_markup' not in kwargs:
            kwargs['reply_markup'] = ReplyKeyboardMarkup([[self.MENU_BUTTON]])

        return self.telegram.send_message(*args, **kwargs)

    def process_update(self, update: Update):
        if update.message:
            self.process_message(update.message)
        elif update.callback_query:
            self.process_callback_query(update.callback_query)
        else:
            self.logger.info('Unhandled update: {}'.format(update))

    def process_message(self, message: Message):
        # Add snippets
        message.u_id = message.from_user.id
        message.moved = False

        # Go back to menu haves the largest priority
        if message.text == self.MENU_BUTTON:
            self.call_handler(message, self.default_handler)
            return

        current_handler = self.user_get(message.u_id, 'next_handler') or self.default_handler
        self.user_set(message.u_id, 'handler', current_handler)
        self.user_set(message.u_id, 'next_handler', '')

        try:
            self.handlers[current_handler](message, self)
        except Exception as error:
            self.logger.error(error)

            self.user_set(message.u_id, 'handler', self.default_handler)

            return

    def process_callback_query(self, query):
        query.u_id = query.from_user.id
        query.message.u_id = query.from_user.id

        handler_name = query.data
        try:
            self.callback_handlers[handler_name](query, self)
        except Exception as error:
            self.telegram.answerCallbackQuery(callback_query_id=query.id)

            if self.debug:
                raise error
            self.logger.error(error)

            self.user_set(query.message.u_id, 'handler', self.default_handler)

            return

        self.telegram.answerCallbackQuery(callback_query_id=query.id)

    def call_handler(self, message, name):
        self.user_set(message.u_id, 'handler', name)
        self.user_set(message.u_id, 'next_handler', '')
        message.moved = True
        self.handlers[name](message, self)

    def user_get(self, user_id, field, default=None):
        key = 'user:{}:{}'.format(user_id, field)
        value = self.redis.get(key) or default
        if type(value) == bytes and field not in self.bytes_fields:
            value = value.decode('utf-8')
        logger.info('redis get {} => {}'.format(key, value))
        return value

    def user_set(self, user_id, field, value, **kwargs):
        key = 'user:{}:{}'.format(user_id, field)
        self.redis.set(key, value, **kwargs)
        logger.info('redis set {} => {}'.format(key, value))

    def user_delete(self, user_id, field):
        key = 'user:{}:{}'.format(user_id, field)
        self.redis.delete(key)
        logger.info('redis delete {}'.format(key))


def call_handler(bot, message, name):
    bot.call_handler(message, name)
