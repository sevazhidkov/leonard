import feedparser
from bs4 import BeautifulSoup
import boto3
import time

while True:
    feed = feedparser.parse('http://www.15minutesoffame.be/9gag/rss/9GAG_-_Trending.atom')['items']
    table = boto3.resource('dynamodb', 'eu-central-1').Table('9gag')
    for item in feed:
        title, post_id, img = item['title'], item['link'].split('/')[4], BeautifulSoup(
            item['summary'], 'lxml'
        )
        if not hasattr(img.find('img'), 'src'):
            img = img.find('a')['href']
        else:
            img = img.find('img')['src']

        table.put_item(
            Item={
                'postId': post_id,
                'title': title,
                'img': img,
                'createdAt': int(time.time()),
                'viewed': []
            }
        )
    time.sleep(10*60)
