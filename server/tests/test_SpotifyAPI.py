"""Test suite for the SpotifyAPI class."""
import os
import unittest
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.sessionManager import SessionManager
from app.APIs.MusicAPI.spotifyAPI import SpotifyAPI


class TestSpotifyAPI(unittest.IsolatedAsyncioTestCase):
    """Tests for the SpotifyAPI class."""

    def setUp(self) -> None:
        """Set up test dependencies before each test."""
        # Set required environment variables.
        os.environ['SPOTIFY_CLIENT_ID'] = 'testClientId'
        os.environ['SPOTIFY_CLIENT_SECRET'] = 'testClientId'

        # Create a fake session manager.
        self.sessionManager: MagicMock = MagicMock(spec=SessionManager)
        self.sessionManager.sessions = {}
        self.sessionManager.getSession.return_value = None
        self.sessionManager.getToken.return_value = 'hostToken'
        self.sessionManager.getHostToken.return_value = 'hostToken'

        # Dummy functions for sendToClient and clearCache.
        self.sendToClient: AsyncMock = AsyncMock()
        self.clearCache: MagicMock = MagicMock()

        # Create the SpotifyAPI instance.
        self.spotifyAPI: SpotifyAPI = SpotifyAPI(
            self.sessionManager,
            hostName='localhost',
            sendToClient=self.sendToClient,
            clearCache=self.clearCache
        )
        # Override REDIRECT_URI for testing purposes.
        self.spotifyAPI.REDIRECT_URI = 'http://localhost/callback'

    @patch('app.APIs.MusicAPI.spotifyAPI.generateRandomString', return_value='fixedSession')
    async def testLogin(self, _mockGenStr: Any) -> None:
        """Test login creates a session and returns a proper redirect."""
        self.sessionManager.getSession.return_value = None

        response: RedirectResponse = await self.spotifyAPI.login(isHost=True)
        self.sessionManager.createSession.assert_called_with('fixedSession', True)
        self.assertIsInstance(response, RedirectResponse)

        # Check that the URL is for Spotify auth with proper query params.
        urlParts = urlparse(response.headers['location'])
        self.assertEqual(urlParts.scheme, 'https')
        self.assertEqual(urlParts.netloc, 'accounts.spotify.com')
        self.assertEqual(urlParts.path, '/authorize/')
        params: Dict[str, Any] = parse_qs(urlParts.query)
        self.assertEqual(params.get('client_id'), ['testClientId'])
        self.assertEqual(params.get('state'), ['fixedSession'])

    async def testCallbackMissingCode(self) -> None:
        """Test callback raises error when code is missing."""
        class FakeRequest:
            """Fake request class for testing."""
            query_params: Dict[str, str] = {}

        with self.assertRaises(HTTPException) as context:
            await self.spotifyAPI.callback(FakeRequest(), 'fixedSession')
        self.assertEqual(context.exception.status_code, 400)

    @patch('app.APIs.MusicAPI.spotifyAPI.requests.post')
    async def testCallbackSuccess(self, mockPost: Any) -> None:
        """Test callback processes a valid Spotify token response."""
        class FakeRequest:
            """Fake request class for testing."""
            query_params: Dict[str, str] = {'code': 'authCode'}

        fakeResponse: MagicMock = MagicMock()
        fakeResponse.json.return_value = {
            'access_token': 'newAccessToken',
            'refresh_token': 'newRefreshToken',
            'expires_in': 3600
        }
        fakeResponse.raise_for_status.return_value = None
        mockPost.return_value = fakeResponse

        self.sessionManager.getSession.return_value = {'isHost': True}
        self.spotifyAPI.getUserID = MagicMock(return_value='testUser')
        self.spotifyAPI.setupPlaylist = MagicMock()

        response: RedirectResponse = await self.spotifyAPI.callback(FakeRequest(), 'fixedSession')
        self.sessionManager.updateSession.assert_called_with('fixedSession', {
            'accessToken': 'newAccessToken',
            'refresh_token': 'newRefreshToken',
            'userID': 'testUser',
        })
        self.sendToClient.assert_awaited_with({'command': 'REFRESH_HOST'})
        self.spotifyAPI.setupPlaylist.assert_called_with('fixedSession', 'Virtual Turntable')
        self.assertIsInstance(response, RedirectResponse)
        self.assertIn('sessionID', response.headers.get('set-cookie', ''))

    @patch('app.APIs.MusicAPI.spotifyAPI.requests.get')
    def testSearchForAlbum(self, mockGet: Any) -> None:
        """Test searchForAlbum returns the expected album ID."""
        fakeJson: Dict[str, Any] = {'albums': {'items': [{'id': 'album123'}]}}
        fakeResponse: MagicMock = MagicMock()
        fakeResponse.json.return_value = fakeJson
        fakeResponse.raise_for_status.return_value = None
        mockGet.return_value = fakeResponse

        albumInfo: Dict[str, str] = {'name': 'Test Album', 'artist': 'Test Artist', 'year': '2021'}
        albumId: str = self.spotifyAPI.searchForAlbum(albumInfo)
        self.assertEqual(albumId, 'album123')

    @patch('app.APIs.MusicAPI.spotifyAPI.requests.put')
    def testPlayPlaylistSuccess(self, mockPut: Any) -> None:
        """Test playPlaylist succeeds when Spotify returns 204."""
        fakeResponse: MagicMock = MagicMock()
        fakeResponse.status_code = 204
        mockPut.return_value = fakeResponse

        self.spotifyAPI.playPlaylist('playlist123')
        mockPut.assert_called_once()

    @patch('app.APIs.MusicAPI.spotifyAPI.requests.put')
    def testPlayPlaylistFailure(self, mockPut: Any) -> None:
        """Test playPlaylist raises HTTPException when Spotify returns an error."""
        fakeResponse: MagicMock = MagicMock()
        fakeResponse.status_code = 400
        fakeResponse.json.return_value = {'error': 'Bad Request'}
        mockPut.return_value = fakeResponse

        with self.assertRaises(HTTPException) as context:
            self.spotifyAPI.playPlaylist('playlist123')
        self.assertEqual(context.exception.status_code, 400)


if (__name__ == '__main__'):
    unittest.main()
