import time
import boto3
import logging
from bs4 import BeautifulSoup
import requests
from boto3.dynamodb.conditions import Key


def main():
    table = boto3.resource('dynamodb', 'eu-west-1').Table('LeonardBot9gagPosts')
    response = table.scan(
        FilterExpression=Key('createdAt').lt(int(time.time()) - 7200)
    )
    logging.info('{} memes to update'.format(response['Count']))
    for meme in response['Items']:
        try:
            points = int(BeautifulSoup(requests.get("http://9gag.com/gag/"+meme["postId"]).text).find('span', {'class' : 'badge-item-love-count'}).get_text().replace(",",""))
        except Exception:
            continue
        table.update_item(
             Key={
                 'postId': meme['postId']
             },
             AttributeUpdates={
                 'points': {
                     'Value': points,
                     'Action': 'PUT'
                 }
             }

         )


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(e)
