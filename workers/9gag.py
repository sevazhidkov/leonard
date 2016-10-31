import os

import feedparser
from bs4 import BeautifulSoup
import boto3
import time

if __name__ == '__main__':
    os.chdir('../')
    while True:
        feed = feedparser.parse('http://www.15minutesoffame.be/9gag/rss/9GAG_-_Trending.atom')['items']
        table = boto3.resource('dynamodb', 'eu-central-1').Table('9gag')
        for item in feed:
            title, post_id, img = item['title'], item['link'].split('/')[4], BeautifulSoup(
                item['summary'], 'lxml'
            ).find('img')
            if not hasattr(img, 'src'):
                continue
            img = img['src']

            table.put_item(
                Item={
                    'postId': post_id,
                    'title': title,
                    'img': img,
                    'createdAt': int(time.time()),
                    'viewed': {-1}
                }
            )
        time.sleep(10*60)
