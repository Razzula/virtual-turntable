"""Discogs API handler."""
from urllib.parse import urlencode
import requests

class DiscogsAPI:
    """Discogs API handler."""

    def __init__(self, apiKey: str, apiSecret: str, version: str, contact: str) -> None:
        """Initialise the Discogs API handler."""

        self.API_KEY = apiKey
        self.API_SECRET = apiSecret

        self.HEADERS = {
            'Authorization': f'Discogs key={self.API_KEY}, secret={self.API_SECRET}',
            'User-Agent': f"Virtual Turntable/{version} ({contact})"
        }

    def searchRelease(self, albumName: str, artistName: str | None, year: str | None, medium: str | None) -> dict[str, str] | None:
        """Get the top result for a given album."""

        params = {
            'release_title': albumName,
            'type': 'release',  # Search only releases
            'per_page': 1       # Limit to the top result
        }
        if (artistName is not None):
            params['artist'] = artistName
        if (year is not None):
            params['year'] = year
        if (medium is not None):
            params['format'] = medium

        url = f'https://api.discogs.com/database/search?{urlencode(params)}'

        response = requests.get(url, headers=self.HEADERS, timeout=10)

        response.raise_for_status()
        data = response.json()
        if (not data['results']):
            if (artistName is not None or year is not None):
                # re-search without artist or year
                return self.searchRelease(albumName, None, None, None)
            return None  # no results found
        return data['results'][0]  # Return the top result

    def getReleaseData(self, releaseID: str) -> list[dict[str, str | int]] | None:
        """Get the images for a given release."""

        url = f'https://api.discogs.com/releases/{releaseID}'

        response = requests.get(url, headers=self.HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        metadata = {}

        formats = data['formats']
        for format in formats:
            if (format['name'] == 'Vinyl'):
                text = format.get('text')
                if (text is not None):
                    text  = text.lower()
                    metadata['colour'] = text.split(' ')[0]

                    if ('marble' in text):
                        metadata['marble'] = True

        return data['images'], metadata

    def downloadImage(self, url: str, path: str) -> None:
        """Download an image from the given URL to the given path."""

        response = requests.get(url, headers=self.HEADERS, timeout=10)
        response.raise_for_status()
        if (response):
            with open(path, 'wb') as file:
                file.write(response.content)
