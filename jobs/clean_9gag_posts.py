import time
import boto3
import logging

from boto3.dynamodb.conditions import Key


def main():
    table = boto3.resource('dynamodb', 'eu-west-1').Table('LeonardBot9gagPosts')
    response = table.scan(
        FilterExpression=(
            Key('createdAt').lt(int(time.time()) - 604800) | Key('img').eq(None)
        )
    )
    logging.info('{} memes to delete'.format(response['Count']))
    for meme in response['Items']:
        table.delete_item(
            Key={
                'postId': meme['postId']
            }
        )


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(e)
