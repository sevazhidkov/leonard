import time

import feedparser
from bs4 import BeautifulSoup
import boto3
from PIL import Image
from io import BytesIO
import requests
import logging

NINEGAG_RSS_URL = 'http://www.15minutesoffame.be/9gag/rss/9GAG_-_Trending.atom'


def main():
    feed = feedparser.parse(NINEGAG_RSS_URL)['items']
    table = boto3.resource('dynamodb', 'eu-west-1').Table('LeonardBot9gagPosts')
    for item in feed:
        title, post_id, img = item['title'], item['link'].split('/')[4], BeautifulSoup(
            item['summary'], 'lxml'
        ).find('img')
        if not hasattr(img, 'src'):
            continue
        img = img['src']

        inp = BytesIO(requests.get(img).content)
        inp.seek(0)
        width, height = Image.open(inp).size
        if height / width >= 2:
            continue
        table.put_item(
            Item={
                'postId': post_id,
                'title': title,
                'img': img,
                'createdAt': int(time.time()),
                'viewed': {-1},
                'file_id': False
            }
        )


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(e)
