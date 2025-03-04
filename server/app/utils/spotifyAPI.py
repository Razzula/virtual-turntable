"""Handler class for Spotify authentication flow."""

import asyncio
import os
import random
import string
import socket
import threading
import time
from typing import Any, Final

from urllib.parse import urlencode
import requests
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.utils.websocketHandler import WebsocketHandler


def getLocalIPs() -> list:
    """Retrieve all local IP addresses (IPv4 and IPv6, including link-local)."""
    ips = set()
    try:
        hostName = socket.gethostname()
        # Add IPv4 addresses
        ips.update(socket.gethostbyname_ex(hostName)[2])
    except Exception as e:
        print(f'Error retrieving IPv4 addresses: {e}')
    try:
        # Add IPv6 addresses
        addrInfos = socket.getaddrinfo(hostName, None, socket.AF_INET6)
        for info in addrInfos:
            ips.add(info[4][0])
    except Exception as e:
        print(f'Error retrieving IPv6 addresses: {e}')
    return list(ips)

class SpotifyAPI:
    """Handler class for Spotify authentication flow."""

    def __init__(self, hostName: str, sendToClient: Any, clearCache: Any) -> None:
        """Initialise the Spotify authentication handler."""
        self.CLIENT_ID: Final = os.getenv('SPOTIFY_CLIENT_ID')
        self.CLIENT_SECRET: Final = os.getenv('SPOTIFY_CLIENT_SECRET')

        self.sendToClient = sendToClient
        self.clearCache = clearCache

        self.REDIRECT_URI: Final = f'https://{hostName}/virtual-turntable/auth/callback'
        print(self.REDIRECT_URI)

        # TODO move these up to main level
        self.sessions: dict[str, dict[str, str]] = {}
        self.vttPlaylistID: str | None = None
        self.hostUserID: str | None = None

    def generateRandomString(self, length: int) -> str:
        """Generate a random string of letters and digits with a given length"""
        return ''.join(
            random.choice(string.ascii_letters + string.digits) for _ in range(length)
        )

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
                'user-modify-playback-state '
            )
        )

        sessionID = self.generateRandomString(16)
        while (self.sessions.get('sessionID')):
            sessionID = self.generateRandomString(16)
        self.sessions[sessionID] = { 'isHost': isHost }

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
        self.sessions[sessionID]['accessToken'] = accessToken
        self.sessions[sessionID]['refresh_token'] = BODY.get('refresh_token')
        self.sessions[sessionID]['userID'] = self.getUserID(sessionID)

        # start token refresh thread
        expiration = BODY.get('expires_in', 3600)
        asyncio.create_task(self.refreshToken(sessionID, expiration))

        # handle setup, for host only
        if (self.sessions[sessionID]['isHost']):
            print('New host connected')
            # terminate existing host sessions
            await self.sendToClient({ 'command': 'REFRESH_HOST' })
            for existingSessionID, session in self.sessions.items():
                if (session is not None):
                    if (session.get('isHost') and sessionID != existingSessionID):
                        self.sessions[existingSessionID] = None
            self.vttPlaylistID = None
            self.clearCache()
            # setup new host
            self.setupPlaylist(sessionID, 'Virtual Turntable')
            self.hostUserID = self.sessions[sessionID]['userID']

        # return to the main page
        response = RedirectResponse(url='/virtual-turntable')
        response.set_cookie(
            key='sessionID',
            value=sessionID,
            httponly=True,
            secure=False, # allow HTTP
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
                        'refresh_token': self.sessions[sessionID]['refresh_token'],
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    auth=(self.CLIENT_ID, self.CLIENT_SECRET),
                    timeout=10,
                )
                RESPONSE.raise_for_status()
                BODY = RESPONSE.json()

                # update tokens
                self.sessions[sessionID]['accessToken'] = BODY.get('accessToken')
                expiration = BODY.get('expires_in', 3600)
                print("Spotify access token refreshed.")

                # inform clients to retrieve the new token
                await self.sendToClient({'command': 'TOKEN'})

            except Exception as e:
                print(f"Error refreshing Spotify token: {e}")
                break

    def token(self, sessionID: str) -> dict[str, str]:
        """Return the Spotify access token."""
        SESSION: Final = self.sessions.get(sessionID)
        if (SESSION):
            ACCESS_TOKEN: Final = SESSION.get('accessToken')
            if (not ACCESS_TOKEN):
                print(f"Access token not found for session '{sessionID}'")
                raise HTTPException(status_code=404, detail='Access token not found.')
            return {'accessToken': ACCESS_TOKEN}
        else:
            print(f"Session '{sessionID}' not found.")
            raise HTTPException(status_code=401, detail='Invalid session.')

    def hostToken(self) -> str:
        hostToken = None
        for session in self.sessions.values():
            if (session and session.get('isHost')):
                hostToken = session.get('accessToken')
                break
        if (hostToken) is None:
            raise HTTPException(
                status_code=404, detail='Host credentials not found.'
            )
        return hostToken

    def playlist(self) -> str:
        """Return the Virtual Turntable playlist ID."""
        PLAYLIST_ID: Final = self.vttPlaylistID
        if (not PLAYLIST_ID):
            raise HTTPException(status_code=404, detail='Playlist ID not found.')
        return PLAYLIST_ID

    def setupPlaylist(self, sessionID: str, playlistName: str) -> None:
        """Fetch/create playlist on Spotify, and cache ID."""
        playlistID = self.getPlaylistByName(sessionID, playlistName)
        if (not playlistID):
            playlistID = self.createPlaylist(sessionID, playlistName)
        self.vttPlaylistID = playlistID

    def getPlaylistByName(self, sessionID: str, playlistName: str) -> str | None:
        """Get the Spotify playlist ID by name."""
        HEADERS: Final = {
            'Authorization': f'Bearer {self.sessions[sessionID].get("accessToken")}'
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
            'Authorization': f'Bearer {self.sessions[sessionID].get("accessToken")}',
            'Content-Type': 'application/json'
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
            'Authorization': f'Bearer {self.sessions[sessionID].get("accessToken")}',
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
            'Authorization': f'Bearer {self.hostToken()}',
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
            'Authorization': f'Bearer {self.hostToken()}',
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
