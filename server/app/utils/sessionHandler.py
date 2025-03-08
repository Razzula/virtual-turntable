"""Handler class for the authentication sessions."""

class SessionManager:
    """Handler class for the authentication sessions."""

    def __init__(self) -> None:
        """Initialise the session handler."""
        self.sessions: dict[str, dict[str, str | bool]] = {}

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
            self.sessions[sessionID].update(values)
