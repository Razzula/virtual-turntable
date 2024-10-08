"""WIP"""
import hashlib
import json
import os
import urllib.request

from dotenv import load_dotenv
import requests

load_dotenv('.env')

# METHOD = 'auth.getMobileSession'
# USERNAME = os.getenv('LASTFM_USERNAME')
# PASSWORD = os.getenv('LASTFM_PASSWORD')
API_KEY = os.getenv('LASTFM_API_KEY')
# API_SIG = hashlib.md5(
#     f'api_key{API_KEY}method{METHOD}password{PASSWORD}username{USERNAME}{os.getenv("LASTFM_SECRET")}'
#     .encode()
# )
# print(API_SIG.hexdigest())

# test = requests.post(
#     'http://ws.audioscrobbler.com/2.0/?format=json',
#     data = {
#         'method': METHOD,
#         'username': USERNAME,
#         'password': PASSWORD,
#         'api_key': API_KEY,
#         'api_sig': API_SIG.hexdigest(),
#     }
# )

# test.raise_for_status()
# key = test.json()['session']['key']

# print(key)

with open('data/albums.json', 'r', encoding='utf-8') as file:
    ALBUMS = json.load(file)
    # TODO: handle errors

for ALBUM in ALBUMS:

    request = requests.post(
        'http://ws.audioscrobbler.com/2.0/?format=json',
        data = {
            'method': 'album.getInfo',
            'artist': ALBUM.get('artist'),
            'album': ALBUM.get('name'),
            'autocorrect': 1,
            'api_key': API_KEY
        },
        timeout=30
    )

    request.raise_for_status()
    response = request.json()

    # print(response)

    # print(response['album']['name'])
    # print(response['album']['artist'])
    # print(response['album']['image'])

    imageURL = response['album']['image'][-1]['#text']
    imageURL = imageURL.replace('u/300x300/', 'u/') # get highest quality image available
    fileExt = imageURL.split('.')[-1]
    print(imageURL)

    urllib.request.urlretrieve(imageURL, f'data/art/{ALBUM.get("name")}.png')
