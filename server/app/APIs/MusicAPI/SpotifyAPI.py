"""Handler class for Spotify authentication flow."""

import asyncio
import os
from typing import Any, Final
from urllib.parse import urlencode

import requests
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.APIs.MusicAPI.IMusicAPI import IMusicAPI
from app.modules.sessionManager import SessionManager
from app.utils import generateRandomString


class SpotifyAPI(IMusicAPI):
    """Handler class for Spotify authentication flow."""

    def __init__(self, sessionManager: SessionManager, hostName: str, sendToClient: Any, clearCache: Any) -> None:
        """Initialise the Spotify authentication handler."""
        super().__init__(sessionManager, hostName, sendToClient, clearCache)
        self.provider = 'Spotify'
        self.CLIENT_ID: Final = os.getenv('SPOTIFY_CLIENT_ID')
        self.CLIENT_SECRET: Final = os.getenv('SPOTIFY_CLIENT_SECRET')

    async def login(self, isHost: bool) -> RedirectResponse:
        """Redirect the user to the Spotify login page."""
        SCOPE: Final = (
            (
                'streaming '  # Manage playback
                # 'user-read-email '  # Access user's email
                'user-read-private '  # Access private account info
                'user-modify-playback-state '  # Control playback
                'playlist-modify-private '  # Create/edit private playlists
                'playlist-modify-public '  # Create/edit public playlists
                'playlist-read-private '  # Access private playlists
            ) if isHost else (
                'playlist-read-private '
                # 'user-modify-playback-state '
            )
        )

        # generate unique session ID
        sessionID = generateRandomString(16)
        while (self.sessionManager.getSession(sessionID)):
            sessionID = generateRandomString(16)
        self.sessionManager.createSession(sessionID, isHost)

        AUTH_QUERY_PARAMS: Final = {
            'response_type': 'code',
            'client_id': self.CLIENT_ID,
            'scope': SCOPE,
            'redirect_uri': self.REDIRECT_URI,
            'state': sessionID,
            'show_dialog': True,
        }
        url = f'https://accounts.spotify.com/authorize/?{urlencode(AUTH_QUERY_PARAMS)}'
        return RedirectResponse(url)

    async def callback(self, request: Request, sessionID: str) -> RedirectResponse:
        """Handle the Spotify auth callback."""

        AUTH_CODE: Final = request.query_params.get('code')
        if (not AUTH_CODE):
            raise HTTPException(status_code=400, detail='Missing authorisation code.')

        RESPONSE: Final = requests.post(
            'https://accounts.spotify.com/api/token',
            data = {
                'grant_type': 'authorization_code',
                'code': AUTH_CODE,
                'redirect_uri': self.REDIRECT_URI,
            },
            auth=(self.CLIENT_ID, self.CLIENT_SECRET),
            timeout=10,
        )

        RESPONSE.raise_for_status()
        BODY: Final = RESPONSE.json()

        accessToken = BODY.get('access_token')

        # store tokens
        self.sessionManager.updateSession(sessionID, {
            'accessToken': accessToken,
            'refresh_token': BODY.get('refresh_token'),
        })
        self.sessionManager.updateSession(sessionID, {
            'userID': self.getUserID(sessionID),
        })

        # start token refresh thread
        expiration = BODY.get('expires_in', 3600)
        asyncio.create_task(self.refreshToken(sessionID, expiration))

        # handle setup, for host only
        if (self.sessionManager.getSession(sessionID)['isHost']):
            print('New host connected')
            # terminate existing host sessions
            await self.sendToClient({ 'command': 'REFRESH_HOST' })
            for (existingSessionID, session) in self.sessionManager.sessions.items():
                if (session is not None):
                    if (session.get('isHost') and sessionID != existingSessionID):
                        self.sessionManager.deleteSession(existingSessionID)
            self.sessionManager.setHostPlaylistID(None)
            self.clearCache()
            # setup new host
            self.setupPlaylist(sessionID, 'Virtual Turntable')


        # return to the main page
        response = RedirectResponse(url='/virtual-turntable')
        response.set_cookie(
            key='sessionID',
            value=sessionID,
            httponly=True,
            secure=False,  # allow HTTP
            samesite='lax'
        )
        return response

    async def refreshToken(self, sessionID: str, expiration: int) -> None:
        """Refresh the access token before it expires."""
        while True:
            # wait until ~1 minute before expiration
            await asyncio.sleep(expiration - 60)

            try:
                RESPONSE = requests.post(
                    'https://accounts.spotify.com/api/token',
                    data={
                        'grant_type': 'refresh_token',
                        'refresh_token': self.sessionManager.getSession(sessionID)['refresh_token'],
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    auth=(self.CLIENT_ID, self.CLIENT_SECRET),
                    timeout=10,
                )
                RESPONSE.raise_for_status()
                BODY = RESPONSE.json()

                # update tokens
                self.sessionManager.updateSession(sessionID, { 'accessToken': BODY.get('access_token') })
                expiration = BODY.get('expires_in', 3600)
                print('Spotify access token refreshed.')

                # inform clients to retrieve the new token
                await self.sendToClient({'command': 'TOKEN'})

            except Exception as e:
                print(f"Error refreshing Spotify token: {e}")
                break

    def setupPlaylist(self, sessionID: str, playlistName: str) -> None:
        """Fetch/create playlist on Spotify, and cache ID."""
        playlistID = self.getPlaylistByName(sessionID, playlistName)
        if (not playlistID):
            playlistID = self.createPlaylist(sessionID, playlistName)
        self.sessionManager.setHostPlaylistID(playlistID)

    def getPlaylistByName(self, sessionID: str, playlistName: str) -> str | None:
        """Get the Spotify playlist ID by name."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.sessionManager.getToken(sessionID)}',
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

    def createPlaylist(self, sessionID: str, playlistName: str) -> str:
        """Create a new Spotify playlist."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.sessionManager.getToken(sessionID)}',
            'Content-Type': 'application/json',
        }

        # define
        url = 'https://api.spotify.com/v1/me/playlists'
        payload = {
            'name': playlistName,
            'description': 'Created with https://github.com/Razzula/virtual-turntable',
            # 'public': False,
        }

        # create
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        playlistData = response.json()

        # return ID
        return str(playlistData['id'])

    def getUserID(self, sessionID: str) -> str:
        """Get user."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.sessionManager.getToken(sessionID)}',
            'Content-Type': 'application/json'
        }

        # define
        url = 'https://api.spotify.com/v1/me'

        # create
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        userData = response.json()

        # return ID
        return str(userData['id'])

    def addAlbumToPlaylist(self, albumID: str, playlistID: str) -> None:
        """Add an album to a Spotify playlist."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.sessionManager.getHostToken()}',
            'Content-Type': 'application/json',
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
            payload = {'uris': trackUris[i : i + 100]}
            response = requests.post(
                addTracksUrl, headers=HEADERS, json=payload, timeout=10
            )
            response.raise_for_status()

    def playPlaylist(self, playlistID: str) -> None:
        """Start playback of the specified Spotify playlist."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.sessionManager.getHostToken()}',
            'Content-Type': 'application/json',
        }

        # define
        url = 'https://api.spotify.com/v1/me/player/play'
        payload = {
            'context_uri': f'spotify:playlist:{playlistID}'
        }

        # request
        response = requests.put(url, headers=HEADERS, json=payload, timeout=10)
        if (response.status_code != 204):
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

    def searchForAlbum(self, album: dict[str, str]) -> str:
        """TODO"""
        AUTH_TOKEN: Final = self.sessionManager.getHostToken()
        
        for medium in ['album']:
            for query in [
                f'{album["name"]} artist:{album["artist"]} year:{album["year"]}',
                f'{album["name"]} artist:{album["artist"]}',
            ]:
                params = {
                    'q': query,
                    'type': medium,
                    'limit': 1,
                }
                request = requests.get(
                    f'https://api.spotify.com/v1/search/?{urlencode(params)}',
                    headers={
                        'Authorization': f'Bearer {AUTH_TOKEN}',
                    },
                    timeout=10,
                )

                request.raise_for_status()
                response = request.json()

                if (len(response['albums']['items']) > 0):
                    return str(response['albums']['items'][0]['id'])
        
        params = {
            'q': f'{album["name"]}',
            'limit': 1,
        }
        request = requests.get(
            f'https://api.spotify.com/v1/search/?{urlencode(params)}',
            headers={
                'Authorization': f'Bearer {AUTH_TOKEN}',
            },
            timeout=10,
        )

        request.raise_for_status()
        response = request.json()

        print(response)
        if (len(response['albums']['items']) > 0):
            return str(response['albums']['items'][0]['id'])

        return None
