"""Test suite for utility functions."""
import string
import unittest
from typing import Any, List

from unittest.mock import patch, MagicMock

from app.utils import getLocalIPs, isHostIP, generateRandomString


class TestUtils(unittest.TestCase):
    """Test suite for utility functions."""

    def test_generateRandomString_lengthAndChars(self) -> None:
        """Test that generateRandomString returns a string of the correct length and allowed characters."""
        length: int = 12
        result: str = generateRandomString(length)
        self.assertEqual(len(result), length)
        allowedChars: str = string.ascii_letters + string.digits
        for char in result:
            self.assertIn(char, allowedChars)

    def test_isHostIP_true(self) -> None:
        """Test isHostIP returns True for an IP in the local IP list."""
        with patch("app.utils.getLocalIPs", return_value=["127.0.0.1", "192.168.1.10"]) as mockGetIPs:
            self.assertTrue(isHostIP("127.0.0.1"))
            self.assertTrue(isHostIP("192.168.1.10"))
            mockGetIPs.assert_called()

    def test_isHostIP_false(self) -> None:
        """Test isHostIP returns False for an IP not in the local IP list or when IP is None."""
        with patch("app.utils.getLocalIPs", return_value=["127.0.0.1", "192.168.1.10"]):
            self.assertFalse(isHostIP("8.8.8.8"))
            self.assertFalse(isHostIP(None))

    @patch("socket.gethostname", return_value="testhost")
    @patch("socket.gethostbyname_ex", return_value=("testhost", [], ["10.0.0.1"]))
    @patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("fe80::1", 0, 0, 0))])
    @patch("socket.socket")
    def test_getLocalIPs(self, mockSocket: Any, mockGetAddrInfo: Any, mockGetHostByNameEx: Any, mockGetHostname: Any) -> None:
        """Test that getLocalIPs aggregates IPv4 and IPv6 addresses from various methods."""
        # Create dummy socket instances for IPv4 and IPv6 that support the context manager.
        dummySocketIPv4: MagicMock = MagicMock()
        dummySocketIPv4.__enter__.return_value.getsockname.return_value = ("192.168.0.1", 0)

        dummySocketIPv6: MagicMock = MagicMock()
        dummySocketIPv6.__enter__.return_value.getsockname.return_value = ("fe80::2", 0, 0, 0)

        # When socket.socket is called twice (for IPv4 and IPv6), return different dummy sockets.
        mockSocket.side_effect = [dummySocketIPv4, dummySocketIPv6]

        ips: list[str] = getLocalIPs()

        # Expected IPs:
        # - From gethostbyname_ex: "10.0.0.1"
        # - From getaddrinfo: "fe80::1"
        # - From dummy IPv4 socket: "192.168.0.1"
        # - From dummy IPv6 socket: "fe80::2"
        expectedIPs: list[str] = ["10.0.0.1", "fe80::1", "192.168.0.1", "fe80::2"]
        for ip in expectedIPs:
            self.assertIn(ip, ips)


if (__name__ == "__main__"):
    unittest.main()
