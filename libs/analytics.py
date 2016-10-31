import time
import boto3

dynamodb = boto3.resource('dynamodb', 'eu-central-1')
table = dynamodb.Table('LeonardBotUserMessage')


def track_message(message):
    table.put_item(Item={
        'id': message.message_id,
        'time': int(time.mktime(message.date.timetuple())),
        'text': message.text,
        'user_id': message.from_user.id,
    })
