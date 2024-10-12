"""Handler class for Spotify authentication flow."""
import os
import random
import string
from typing import Final

from urllib.parse import urlencode
import requests
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

class SpotifyAuth:
    """Handler class for Spotify authentication flow."""

    REDIRECT_URI: Final = 'http://localhost:1948/virtual-turntable/auth/callback'

    def __init__(self) -> None:
        """Initialise the Spotify authentication handler."""
        self.CLIENT_ID: Final = os.getenv('SPOTIFY_CLIENT_ID')
        self.CLIENT_SECRET: Final = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.tokens:dict[str, str] = {}

    def generateRandomString(self, length: int) -> str:
        """Generate a random string of letters and digits with a given length"""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    async def login(self) -> RedirectResponse:
        """Redirect the user to the Spotify login page."""
        SCOPE: Final = 'streaming user-read-email user-read-private user-modify-playback-state'
        STATE: Final = self.generateRandomString(16)

        AUTH_QUERY_PARAMS: Final = {
            'response_type': "code",
            'client_id': self.CLIENT_ID,
            'scope': SCOPE,
            'redirect_uri': self.REDIRECT_URI,
            'state': STATE
        }
        url = f'https://accounts.spotify.com/authorize/?{urlencode(AUTH_QUERY_PARAMS)}'
        return RedirectResponse(url)

    async def callback(self, request: Request) -> RedirectResponse:
        """Handle the Spotify auth callback."""

        AUTH_CODE: Final = request.query_params.get('code')
        if (not AUTH_CODE):
            raise HTTPException(status_code=400, detail='Missing authorisation code.')

        RESPONSE: Final = requests.post(
            'https://accounts.spotify.com/api/token',
            data = {
                'code': AUTH_CODE,
                'redirect_uri': self.REDIRECT_URI,
                'grant_type': 'authorization_code'
            },
            auth=(self.CLIENT_ID, self.CLIENT_SECRET),
            timeout=10
        )

        RESPONSE.raise_for_status()
        BODY: Final = RESPONSE.json()
        self.tokens['access_token'] = BODY.get('access_token')

        return RedirectResponse(url='/')

    def token(self) -> dict[str, str]:
        """Return the Spotify access token."""

        ACCESS_TOKEN: Final = self.tokens.get('access_token')
        if (not ACCESS_TOKEN):
            raise HTTPException(status_code=404, detail='Access token not found.')
        return {'access_token': ACCESS_TOKEN}
