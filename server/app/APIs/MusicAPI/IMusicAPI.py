"""Interface for music authentication and playback APIs."""

from abc import ABC, abstractmethod
from typing import Any, Final

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.modules.sessionManager import SessionManager

class IMusicAPI(ABC):
    """Interface for music authentication and playback APIs."""

    def __init__(self, sessionManager: SessionManager, hostName: str, sendToClient: Any, clearCache: Any) -> None:
        """Initialise the Spotify authentication handler."""
        self.provider = None
        self.sendToClient = sendToClient
        self.clearCache = clearCache

        self.REDIRECT_URI: Final = f'https://{hostName}/virtual-turntable/auth/callback'
        print(self.REDIRECT_URI)

        self.sessionManager = sessionManager

    def getProviderName(self) -> str:
        """Get the name of the music provider."""
        if (self.provider is None):
            raise NotImplementedError('Provider not set.')
        return self.provider

    @abstractmethod
    async def login(self, isHost: bool) -> RedirectResponse:
        """Redirect the user to the API's login page."""
        raise NotImplementedError

    @abstractmethod
    async def callback(self, request: Request, sessionID: str) -> RedirectResponse:
        """Handle the API authentication callback."""
        raise NotImplementedError

    @abstractmethod
    async def refreshToken(self, sessionID: str, expiration: int) -> None:
        """Refresh the access token before it expires."""
        raise NotImplementedError

    @abstractmethod
    def setupPlaylist(self, sessionID: str, playlistName: str) -> None:
        """Fetch or create a playlist on the API and cache its ID."""
        raise NotImplementedError

    @abstractmethod
    def getPlaylistByName(self, sessionID: str, playlistName: str) -> str | None:
        """Retrieve the playlist ID by its name."""
        raise NotImplementedError

    @abstractmethod
    def createPlaylist(self, sessionID: str, playlistName: str) -> str:
        """Create a new playlist."""
        raise NotImplementedError

    @abstractmethod
    def getUserID(self, sessionID: str) -> str:
        """Retrieve the user ID."""
        raise NotImplementedError

    @abstractmethod
    def addAlbumToPlaylist(self, albumID: str, playlistID: str) -> None:
        """Add an album to a playlist."""
        raise NotImplementedError

    @abstractmethod
    def playPlaylist(self, playlistID: str) -> None:
        """Start playback of the specified playlist."""
        raise NotImplementedError

    @abstractmethod
    def searchForAlbum(self, query: str) -> str:
        """Search for an album and return its ID."""
        raise NotImplementedError
