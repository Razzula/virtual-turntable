"""WIP"""
import json
import os
import re
import time
import urllib.request
import urllib.parse

from dotenv import load_dotenv
import requests

load_dotenv('.env')
root = os.path.dirname(os.path.abspath(__file__))

VERSION = os.getenv('VERSION')
CONTACT = os.getenv('CONTACT')

VERBOSITY = int(os.getenv('VERBOSITY') or 0)
EXPRESS = True  # flag to skip albums that have already been processed (note: this may be overaggresive)

HEADERS = {
    'Accept': 'application/json',
    'User-Agent': f"Virtual Turntable/{VERSION} ({CONTACT})"
}

index: dict[str, dict[str, str]] = {}

with open(os.path.join(root, 'data/albums.json'), 'r', encoding='utf-8') as file:
    ALBUMS = json.load(file)
    # TODO: handle errors

def makeRequest(url: str) -> requests.Response | None:
    """Make a request to the given URL, with exponential backoff and retries."""

    retries = 5
    delay = 15

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            if (attempt < retries - 1):
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            raise e

    return None

def downloadImage(url: str, path: str) -> None:
    """Download an image from the given URL to the given path."""

    response = makeRequest(url)
    if (response):
        with open(path, 'wb') as file:
            file.write(response.content)

def main() -> None:

    validAlbum = False

    validAlbumCount = 0
    validImageCount = 0
    imageDownloadCount = 0

    for album in ALBUMS:
        validAlbum = False

        artist = album['artist'].replace(' ', '')
        albumID = f"{album['name'].replace(' ', '')}_{artist}_{album['year']}"
        albumID = re.sub(r'[<>:"/\\|?*]', '', albumID)
        # we artifically create an ID for the album, based on its name, artist, and year

        if (EXPRESS and os.path.exists(os.path.join(root, 'data/art/', albumID))):
            if (VERBOSITY > 2):
                print(album.get('name'), album.get('artist'), album.get('year'))
            index[albumID] = album
            continue # skip albums that have already been processed
        else:
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
            timeout=60,
        )

        request.raise_for_status()
        response = request.json()

        if (response['count'] == 0):
            if (VERBOSITY > 0):
                print(f"\tAlbum not found! [{album.get('name')}]")
            time.sleep(1)  # enforce rate limiting
            continue
        mbid = response['release-groups'][0]['id']

        if (VERBOSITY > 1):
            print('\t', mbid)

        # FIND ALBUM ART
        retries = 5
        delay = 15
        for i in range(retries):
            try:
                request = requests.get(
                    f'https://coverartarchive.org/release-group/{mbid}',
                    headers = HEADERS,
                    timeout=60,
                )
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                if (i < retries - 1):
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    # raise  # Raise the error if retries are exhausted
                    pass

        if (request.status_code == 404):
            continue # Siamese Dream The Smashing Pumpkins 1993
        request.raise_for_status()
        response = request.json()

        frontURL = None
        backURL = None
        if (response.get('images') is not None):
            for image in response['images']:
                if (image['front']):
                    if (frontURL is None):
                        frontURL = image['image']
                elif (image['back']):
                    if (backURL is None):
                        backURL = image['image']

                if (frontURL is not None and backURL is not None):
                    break
        else:
            if (VERBOSITY > 0):
                print(f"\tNo images found! [{album.get('name')}]")
            continue

        # DOWNLOAD IMAGE(S)

        if (not os.path.exists(os.path.join(root, 'data/art/', artist, albumID))):
            os.makedirs(os.path.join(root, 'data/art/', artist, albumID))

        if (frontURL is not None):
            validAlbum = True
            validImageCount += 1
            path = os.path.join(root, 'data/art/', artist, albumID, 'front.png')
            if (os.path.exists(path)):
                if (VERBOSITY > 2):
                    print('\t', frontURL, '[x]')
            else:
                downloadImage(frontURL, path)
                imageDownloadCount += 1
                if (VERBOSITY > 0):
                    print('\t', frontURL, '[/]')
        if (backURL is not None):
            validAlbum = True
            validImageCount += 1
            path = os.path.join(root, 'data/art/', artist, albumID, 'back.png')
            if (os.path.exists(path)):
                if (VERBOSITY > 2):
                    print('\t', backURL, '[x]')
            else:
                downloadImage(backURL, path)
                imageDownloadCount += 1
                if (VERBOSITY > 0):
                    print('\t', backURL, '[/]')

        index[albumID] = album

        if (validAlbum):
            validAlbumCount += 1

    with open(os.path.join(root, 'data', 'manifest.json'), 'w', encoding='utf-8') as file:
        json.dump(index, file, ensure_ascii=False, indent=4)

    if (VERBOSITY > 0):
        if (VERBOSITY > 2):
            print()
        print(f'Collected {validImageCount} images ({imageDownloadCount} downloaded) for {validAlbumCount} albums (out of {len(ALBUMS)} requested).')

main()
