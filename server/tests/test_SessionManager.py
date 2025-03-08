"""Test suite for the SessionManager class."""
import unittest
from typing import Dict, Union

from fastapi import HTTPException
from app.modules.sessionManager import SessionManager 


class TestSessionManager(unittest.TestCase):
    """Test suite for the SessionManager class."""

    def setUp(self) -> None:
        """Set up a new SessionManager for each test."""
        self.manager: SessionManager = SessionManager()

    def testCreateSession(self) -> None:
        """Test that createSession adds a session with the correct host flag."""
        sessionID: str = "session1"
        self.manager.createSession(sessionID, True)
        session: Dict[str, Union[str, bool]] = self.manager.getSession(sessionID)
        self.assertTrue(session.get("isHost", False))

    def testDeleteSession(self) -> None:
        """Test that deleteSession removes an existing session."""
        sessionID: str = "session2"
        self.manager.createSession(sessionID, False)
        self.manager.deleteSession(sessionID)
        session: Dict[str, Union[str, bool]] = self.manager.getSession(sessionID)
        self.assertEqual(session, {})

    def testUpdateSessionAndHostUserID(self) -> None:
        """Test that updateSession updates values and sets hostUserID if session is host."""
        sessionID: str = "session3"
        self.manager.createSession(sessionID, True)
        values: Dict[str, str] = {"accessToken": "abc", "userID": "user123"}
        self.manager.updateSession(sessionID, values)
        session: Dict[str, Union[str, bool]] = self.manager.getSession(sessionID)
        self.assertEqual(session.get("accessToken"), "abc")
        self.assertEqual(self.manager.getHostUserID(), "user123")

        # Test non-host session update does not affect hostUserID.
        sessionID2: str = "session4"
        self.manager.createSession(sessionID2, False)
        self.manager.updateSession(sessionID2, {"accessToken": "def", "userID": "user456"})
        session2: Dict[str, Union[str, bool]] = self.manager.getSession(sessionID2)
        self.assertEqual(session2.get("accessToken"), "def")
        # Host user should remain unchanged from the previous host session.
        self.assertEqual(self.manager.getHostUserID(), "user123")

    def testSetAndGetHostPlaylistID(self) -> None:
        """Test setting and getting the host playlist ID."""
        self.manager.setHostPlaylistID("playlist123")
        self.assertEqual(self.manager.getHostPlaylistID(), "playlist123")
        self.manager.setHostPlaylistID(None)
        self.assertIsNone(self.manager.getHostPlaylistID())

    def testSetAndGetHostUserID(self) -> None:
        """Test setting and getting the host user ID."""
        self.manager.setHostUserID("user999")
        self.assertEqual(self.manager.getHostUserID(), "user999")

    def testGetHostToken(self) -> None:
        """Test that getHostToken returns the access token of the first host session found."""
        self.manager.createSession("hostSession", True)
        self.manager.updateSession("hostSession", {"accessToken": "hostTokenValue"})
        self.manager.createSession("userSession", False)
        self.manager.updateSession("userSession", {"accessToken": "userTokenValue"})
        hostToken: Union[str, None] = self.manager.getHostToken()
        self.assertEqual(hostToken, "hostTokenValue")

    def testGetTokenSuccess(self) -> None:
        """Test that getToken returns the correct access token when it exists."""
        sessionID: str = "session5"
        self.manager.createSession(sessionID, False)
        self.manager.updateSession(sessionID, {"accessToken": "token123"})
        token: str = self.manager.getToken(sessionID)
        self.assertEqual(token, "token123")

    def testGetTokenNoToken(self) -> None:
        """Test that getToken raises an HTTPException when no access token exists."""
        sessionID: str = "session6"
        self.manager.createSession(sessionID, False)
        with self.assertRaises(HTTPException) as context:
            self.manager.getToken(sessionID)
        self.assertEqual(context.exception.status_code, 404)

    def testGetTokenInvalidSession(self) -> None:
        """Test that getToken raises an HTTPException for a non-existent session."""
        with self.assertRaises(HTTPException) as context:
            self.manager.getToken("nonexistent")
        self.assertEqual(context.exception.status_code, 401)


if (__name__ == "__main__"):
    unittest.main()
