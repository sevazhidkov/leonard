import os
import time
import json
import requests


def get_timezone(lat, long):
    response = requests.get('https://maps.googleapis.com/maps/api/timezone/json', params={
        'location': '{},{}'.format(lat, long),
        'timestamp': int(time.time()),
        'key': os.environ['GOOGLE_API_TOKEN']
    }).json()
    return response['timeZoneId']


def shorten_url(url):
    response = requests.post(
        'https://www.googleapis.com/urlshortener/v1/url?key={}'.format(os.environ['GOOGLE_API_TOKEN']),
        data=json.dumps({'longUrl': url}), headers={'Content-Type': 'application/json'}
    ).json()
    print('Google Shortener url:', url, '; response:', response)
    return response['id']
