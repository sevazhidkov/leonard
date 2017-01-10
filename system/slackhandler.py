import logging
from slacker import Slacker
import os


class SlackHandler(logging.Handler):
    def __init__(self, slack_token):
        logging.Handler.__init__(self)
        self.slack = Slacker(slack_token)

    def emit(self, record):
        if record.name != 'Unauthorized':
            self.slack.chat.post_message('#leonard', text='ERROR ON {}\n{}'.format(
                'DEBUG' if os.environ.get('BOT_DEBUG', '0') == '1' else 'PRODUCTION @channel',
                record
            ), parse='full')
