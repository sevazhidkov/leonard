import os
import time
import boto3
import json
import requests

dynamodb = boto3.client('dynamodb', 'eu-west-1')


class Tracker:
    def __init__(self, plugin_name, update=None, u_id=None):
        self.plugin = plugin_name

        # Events, for example, uber-make-order, uber-cancel-order
        self.events = []
        # Timers, for example, uber-make-order-request,  vinci-filter-download
        self.timers = []

        if update:
            self.u_id = update.u_id
        else:
            self.u_id = u_id

        self.timer_start = {}

    def event(self, event_type, params=None):
        self.events.append({
            'type': event_type,
            'plugin_name': self.plugin,
            'time': time.time(),
            'params': params,
            'u_id': self.u_id
        })

    def timer_start(self, timer_name):
        self.timer_start[timer_name] = time.time()

    def fix_timer(self, timer_name, params=None):
        finish_time = time.time()
        self.timers.append({'name': timer_name,
                            'start_time': self.timer_start[timer_name],
                            'finish_time': finish_time,
                            'time': finish_time - self.timer_start[timer_name],
                            'params': params,
                            'plugin_name': self.plugin,
                            'u_id': self.u_id})

    def send(self):
        for event in self.events:
            dynamodb.put_item(
                TableName='LeonardBotEvent',
                Item=prepare_to_dynamo(event)
            )
        for timer in self.timers:
            dynamodb.put_item(
                TableName='LeonardBotTimer',
                Item=prepare_to_dynamo(timer)
            )


def send_to_amplitude(bot, message, handler):
    event = {
        'id': message.message_id,
        'time': time.mktime(message.date.timetuple()),
        'proceed_time': time.time(),
        'user_id': message.from_user.id,
        'event_type': handler,
        'event_properties': {
            'text': message.text
        }
    }
    location = bot.user_get(message.from_user.id, 'location', '')
    if location:
        location = json.loads(location)
        event['country'] = location['country']
        event['city'] = location['name']
    requests.post('https://api.amplitude.com/httpapi', data={
        'api_key': os.environ['AMPLITUDE_API_KEY'],
        'event': json.dumps([event])
    })


def track_message(bot, message, handler, tracker=None):
    dynamodb.put_item(
        TableName='LeonardBotUserMessage',
        Item=prepare_to_dynamo({
            'id': message.message_id,
            'time': time.mktime(message.date.timetuple()),
            'proceed_time': time.time(),
            'text': message.text,
            'user_id': message.from_user.id,
            'handler': handler
        })
    )

    if tracker:
        tracker.send()
    send_to_amplitude(bot, message, handler)


def prepare_to_dynamo(item):
    dynamo_item = {}
    for (key, value) in item.items():
        if value == '':
            continue
        if type(value) == str:
            dynamo_item[key] = {'S': value}
        elif type(value) in [int, float]:
            dynamo_item[key] = {'N': str(value)}
        elif type(value) == dict:
            dynamo_item[key] = {'M': prepare_to_dynamo(value)}
        elif type(value) == list:
            dynamo_item[key] = {'L': []}
            for i in value:
                dynamo_item[key]['L'].append(prepare_to_dynamo(i))
        elif value is None:
            continue
        else:
            raise TypeError('Unknown data type for DynamoDB')
    return dynamo_item
