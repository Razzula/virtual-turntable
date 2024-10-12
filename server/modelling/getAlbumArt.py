"""WIP"""
import json
import os
import urllib.request
import urllib.parse

from dotenv import load_dotenv
import requests

load_dotenv('.env')
root = os.path.dirname(os.path.abspath(__file__))

VERSION = os.getenv('VERSION')
CONTACT = os.getenv('CONTACT')

HEADERS = {
    'Accept': 'application/json',
    'User-Agent': f"Virtual Turntable/{VERSION} ({CONTACT})"
}

index: dict[str, dict[str, str]] = {}

with open(os.path.join(root, 'data/albums.json'), 'r', encoding='utf-8') as file:
    ALBUMS = json.load(file)
    # TODO: handle errors

for album in ALBUMS:
    print(album.get('name'), album.get('artist'), album.get('year'))

    # note: requests to musicbrainz are rate-limited. The average rate must be <= 1 request per second.
    # however, the time taken to download the images ensures that we will not exceed this rate.
    # hence, no explicitly rate limiting has been implemented.

    # FIND ALBUM MBID
    query = urllib.parse.quote(
        f'releasegroup:"{album.get("name")}" AND artist:"{album.get("artist")}" AND primarytype:"album" AND firstreleasedate:"{album.get("year")}"'
    )

    request = requests.get(
        f'https://musicbrainz.org/ws/2/release-group/?query={query}',
        headers = HEADERS,
        timeout=5
    )

    request.raise_for_status()
    response = request.json()

    if (response['count'] == 0):
        print(f"Album not found: {album.get('name')}")
        continue
    mbid = response['release-groups'][0]['id']

    # FIND ALBUM ART
    request = requests.get(
        f'https://coverartarchive.org/release-group/{mbid}',
        headers = HEADERS,
        timeout=5
    )

    request.raise_for_status()
    response = request.json()

    frontURL = None
    backURL = None
    for image in response['images']:
        if (image['front']):
            if (frontURL is None):
                frontURL = image['image']
        elif (image['back']):
            if (backURL is None):
                backURL = image['image']

        if (frontURL is not None and backURL is not None):
            break

    # DOWNLOAD IMAGE(S)
    albumID = f"{album['name'].replace(' ', '')}_{album['artist'].replace(' ', '')}_{album['year']}"
    # we artifically create an ID for the album, based on its name, artist, and year

    if (not os.path.exists(os.path.join(root, 'data/art/', albumID))):
        os.makedirs(os.path.join(root, 'data/art/', albumID))

    if (frontURL is not None):
        path = os.path.join(root, 'data/art/', albumID, 'front.png')
        if (os.path.exists(path)):
            print('\t', frontURL, '')
        else:
            urllib.request.urlretrieve(frontURL, path)
            print('\t', frontURL, '')
    if (backURL is not None):
        path = os.path.join(root, 'data/art/', albumID, 'back.png')
        if (os.path.exists(path)):
            print('\t', backURL, '')
        else:
            urllib.request.urlretrieve(backURL, path)
            print('\t', backURL, '')

    index[albumID] = album

with open(os.path.join(root, 'data', 'manifest.json'), 'w', encoding='utf-8') as file:
    json.dump(index, file, ensure_ascii=False, indent=4)
