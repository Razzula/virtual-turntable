"""Handler class for Spotify authentication flow."""
import os
import random
import string
from typing import Final

from urllib.parse import urlencode
import requests
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

class SpotifyAPI:
    """Handler class for Spotify authentication flow."""

    REDIRECT_URI: Final = 'http://localhost:1948/virtual-turntable/auth/callback'

    def __init__(self) -> None:
        """Initialise the Spotify authentication handler."""
        self.CLIENT_ID: Final = os.getenv('SPOTIFY_CLIENT_ID')
        self.CLIENT_SECRET: Final = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.tokens: dict[str, str] = {}
        self.vttPlaylistID: str | None = None

    def generateRandomString(self, length: int) -> str:
        """Generate a random string of letters and digits with a given length"""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    async def login(self) -> RedirectResponse:
        """Redirect the user to the Spotify login page."""
        SCOPE: Final = (
            'streaming '  # Manage playback
            'user-read-email '  # Access user's email
            'user-read-private '  # Access private account info
            'user-modify-playback-state '  # Control playback
            'playlist-modify-private '  # Create/edit private playlists
            'playlist-modify-public'  # Create/edit public playlists
        )

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

    def playlist(self) -> str:
        """Return the Virtual Turntable playlist ID."""
        PLAYLIST_ID: Final = self.vttPlaylistID
        if (not PLAYLIST_ID):
            raise HTTPException(status_code=404, detail='Playlist ID not found.')
        return PLAYLIST_ID

    def setupPlaylist(self, playlistName: str) -> None:
        """Fetch/create playlist on Spotify, and cache ID."""
        playlistID = self.getPlaylistByName(playlistName)
        if (not playlistID):
            playlistID = self.createPlaylist(playlistName)
        self.vttPlaylistID = playlistID

    def getPlaylistByName(self, playlistName: str) -> str | None:
        """Get the Spotify playlist ID by name."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.tokens.get("access_token")}'
        }
        url = 'https://api.spotify.com/v1/me/playlists'
        while (url):
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            body = response.json()

            for playlist in body.get('items', []):
                if playlist['name'].lower() == playlistName.lower():
                    return str(playlist['id'])

            # handle pagination
            url = body.get('next')

        return None

    def createPlaylist(self, playlistName: str) -> str:
        """Create a new Spotify playlist."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.tokens.get("access_token")}',
            'Content-Type': 'application/json'
        }

        # define
        url = 'https://api.spotify.com/v1/me/playlists'
        payload = {
            'name': playlistName,
            'description': 'Created with https://github.com/Razzula/virtual-turntable',
            'public': False,
        }

        # create
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        playlistData = response.json()

        # return ID
        return str(playlistData['id'])

    def addAlbumToPlaylist(self, albumID: str, playlistID: str) -> None:
        """Add an album to a Spotify playlist."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.tokens.get("access_token")}',
            'Content-Type': 'application/json'
        }

        # get tracks
        albumUrl = f'https://api.spotify.com/v1/albums/{albumID}/tracks'
        response = requests.get(albumUrl, headers=HEADERS, timeout=10)
        response.raise_for_status()
        tracks = response.json().get('items', [])

        if (not tracks):
            raise ValueError(f"No tracks found for album ID '{albumID}'")

        # extract URIs
        trackUris = [track['uri'] for track in tracks]

        # add tracks in batches of 100 (Spotify API limitation)
        addTracksUrl = f'https://api.spotify.com/v1/playlists/{playlistID}/tracks'
        for i in range(0, len(trackUris), 100):
            payload = {'uris': trackUris[i:i+100]}
            response = requests.post(addTracksUrl, headers=HEADERS, json=payload, timeout=10)
            response.raise_for_status()

    def playPlaylist(self, playlistID: str) -> None:
        """Start playback of the specified Spotify playlist."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.tokens.get("access_token")}',
            'Content-Type': 'application/json'
        }

        # define
        url = 'https://api.spotify.com/v1/me/player/play'
        payload = {
            'context_uri': f'spotify:playlist:{playlistID}'
        }

        # request
        response = requests.put(url, headers=HEADERS, json=payload, timeout=10)
        if (response.status_code != 204):
            raise HTTPException(status_code=response.status_code, detail=response.json())
