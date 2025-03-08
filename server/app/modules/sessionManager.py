"""Handler class for the authentication sessions."""

from typing import Final

from fastapi import HTTPException


class SessionManager:
    """Handler class for the authentication sessions."""

    def __init__(self) -> None:
        """Initialise the session handler."""
        self.sessions: dict[str, dict[str, str | bool]] = {}
        self.hostPlaylistID: str | None = None
        self.hostUserID: str | None = None

    def createSession(self, sessionID: str, isHost: bool) -> None:
        """Create a new session for the user."""
        self.sessions[sessionID] = { 'isHost': isHost }

    def deleteSession(self, sessionID: str) -> None:
        """Delete the session for the user."""
        self.sessions.pop(sessionID, None)

    def getSession(self, sessionID: str) -> dict[str, str | bool]:
        """Get the session for the user."""
        return self.sessions.get(sessionID, {})

    def updateSession(self, sessionID: str, values: dict[str, str]) -> None:
        """Update the session for the user."""
        session = self.getSession(sessionID)
        if (session):
            for (key, value) in values.items():
                self.sessions[sessionID][key] = value

        if (session.get('isHost')):
            if (values.get('userID')):
                self.setHostUserID(values['userID'])

    def setHostPlaylistID(self, hostPlaylistID: str | None) -> None:
        """Setter for hostPlaylistID"""
        self.hostPlaylistID = hostPlaylistID

    def getHostPlaylistID(self) -> str | None:
        """Getter for hostPlaylistID"""
        return self.hostPlaylistID

    def setHostUserID(self, hostUserID: str) -> None:
        """Setter for hostUserID"""
        self.hostUserID = hostUserID

    def getHostUserID(self) -> str | None:
        """Getter for hostUserID"""
        return self.hostUserID

    def getHostToken(self) -> str | None:
        """Return the access token for the host."""
        hostToken = None
        for session in self.sessions.values():
            if (session and session.get('isHost')):
                token = session.get('accessToken')
                if (token is not None):
                    hostToken = str(token)
                break
        return hostToken

    def getToken(self, sessionID: str) -> str:
        """Return the access token."""
        SESSION: Final = self.getSession(sessionID)
        if (SESSION):
            ACCESS_TOKEN: Final = SESSION.get('accessToken', None)
            if (not ACCESS_TOKEN):
                print(f"Access token not found for session '{sessionID}'")
                raise HTTPException(status_code=404, detail='Access token not found.')
            return str(ACCESS_TOKEN)
        else:
            print(f"Session '{sessionID}' not found.")
            raise HTTPException(status_code=401, detail='Invalid session.')