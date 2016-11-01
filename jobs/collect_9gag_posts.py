import os
import time

import feedparser
from bs4 import BeautifulSoup
import boto3

NINEGAG_RSS_URL = 'http://www.15minutesoffame.be/9gag/rss/9GAG_-_Trending.atom'

if __name__ == '__main__':
    feed = feedparser.parse(NINEGAG_RSS_URL)['items']
    table = boto3.resource('dynamodb', 'eu-west-1').Table('LeonardBot9gagPosts')
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