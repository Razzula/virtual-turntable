import unittest
from typing import Any, Dict, List, Optional

from unittest.mock import patch, MagicMock, mock_open

from app.APIs.discogsAPI import DiscogsAPI


class TestDiscogsAPI(unittest.TestCase):
    """Test suite for the DiscogsAPI class."""

    def setUp(self) -> None:
        """Set up test dependencies before each test."""
        self.apiKey: str = "testKey"
        self.apiSecret: str = "testSecret"
        self.version: str = "1.0.0"
        self.contact: str = "test@example.com"
        self.discogs: DiscogsAPI = DiscogsAPI(self.apiKey, self.apiSecret, self.version, self.contact)

    @patch("app.APIs.discogsAPI.requests.get")
    def test_searchRelease_success(self, mockGet: Any) -> None:
        """Test searchRelease returns the top result when results are present."""
        # Prepare dummy response data.
        dummyResult: Dict[str, str] = {"id": "123", "title": "Test Release"}
        dummyData: Dict[str, Any] = {"results": [dummyResult]}
        dummyResponse: MagicMock = MagicMock()
        dummyResponse.json.return_value = dummyData
        dummyResponse.raise_for_status.return_value = None
        mockGet.return_value = dummyResponse

        result: Optional[Dict[str, str]] = self.discogs.searchRelease("Album", "Artist", "2020", "Vinyl")
        self.assertEqual(result, dummyResult)

        # Verify that the URL was constructed correctly.
        args, kwargs = mockGet.call_args
        url: str = args[0]
        self.assertIn("release_title=Album", url)
        self.assertIn("artist=Artist", url)
        self.assertIn("year=2020", url)
        self.assertIn("format=Vinyl", url)

    @patch("app.APIs.discogsAPI.requests.get")
    def test_searchRelease_fallback(self, mockGet: Any) -> None:
        """Test searchRelease re-searches without extra params if no results found initially."""
        # First call: no results.
        dummyDataEmpty: Dict[str, Any] = {"results": []}
        dummyResponseEmpty: MagicMock = MagicMock()
        dummyResponseEmpty.json.return_value = dummyDataEmpty
        dummyResponseEmpty.raise_for_status.return_value = None

        # Second call: returns a result.
        dummyResult: Dict[str, str] = {"id": "456", "title": "Fallback Release"}
        dummyDataSuccess: Dict[str, Any] = {"results": [dummyResult]}
        dummyResponseSuccess: MagicMock = MagicMock()
        dummyResponseSuccess.json.return_value = dummyDataSuccess
        dummyResponseSuccess.raise_for_status.return_value = None

        # Side effect: first call returns empty, second call returns valid result.
        mockGet.side_effect = [dummyResponseEmpty, dummyResponseSuccess]

        result: Optional[Dict[str, str]] = self.discogs.searchRelease("Album", "Artist", "2020", "Vinyl")
        self.assertEqual(result, dummyResult)
        self.assertEqual(mockGet.call_count, 2)

    @patch("app.APIs.discogsAPI.requests.get")
    def test_searchRelease_noResults(self, mockGet: Any) -> None:
        """Test searchRelease returns None if no results are found even after fallback."""
        dummyDataEmpty: Dict[str, Any] = {"results": []}
        dummyResponseEmpty: MagicMock = MagicMock()
        dummyResponseEmpty.json.return_value = dummyDataEmpty
        dummyResponseEmpty.raise_for_status.return_value = None

        # Both calls return empty results.
        mockGet.side_effect = [dummyResponseEmpty, dummyResponseEmpty]

        result: Optional[Dict[str, str]] = self.discogs.searchRelease("Album", "Artist", "2020", "Vinyl")
        self.assertIsNone(result)
        self.assertEqual(mockGet.call_count, 2)

    @patch("app.APIs.discogsAPI.requests.get")
    def test_getDataForRelease(self, mockGet: Any) -> None:
        """Test that getDataForRelease returns images and formatted metadata."""
        # Prepare dummy release data.
        dummyImages: List[Dict[str, Any]] = [{"uri": "http://example.com/image1.jpg"}]
        dummyFormats: List[Dict[str, Any]] = [{
            "name": "Vinyl",
            "text": "Red Marble Edition"
        }]
        dummyData: Dict[str, Any] = {
            "images": dummyImages,
            "formats": dummyFormats
        }
        dummyResponse: MagicMock = MagicMock()
        dummyResponse.json.return_value = dummyData
        dummyResponse.raise_for_status.return_value = None
        mockGet.return_value = dummyResponse

        images, metadata = self.discogs.getDataForRelease("789")
        self.assertEqual(images, dummyImages)
        # The first word "red" should be used for colour and marble detected.
        self.assertEqual(metadata.get("colour"), "red")
        self.assertTrue(metadata.get("marble"))

        # Verify URL formation.
        args, kwargs = mockGet.call_args
        url: str = args[0]
        self.assertIn("/releases/789", url)

    @patch("app.APIs.discogsAPI.requests.get")
    def test_downloadImage(self, mockGet: Any) -> None:
        """Test that downloadImage writes response content to a file."""
        dummyContent: bytes = b"image bytes"
        dummyResponse: MagicMock = MagicMock()
        dummyResponse.content = dummyContent
        dummyResponse.raise_for_status.return_value = None
        mockGet.return_value = dummyResponse

        dummyURL: str = "http://example.com/image.jpg"
        dummyPath: str = "dummy_image.jpg"

        # Patch open so that no actual file is written.
        m_open = mock_open()
        with patch("builtins.open", m_open, create=True):
            self.discogs.downloadImage(dummyURL, dummyPath)

        # Ensure that requests.get was called with correct parameters.
        mockGet.assert_called_with(dummyURL, headers=self.discogs.HEADERS, timeout=10)
        # Verify that the file was opened in binary write mode and written to.
        m_open.assert_called_with(dummyPath, "wb")
        m_open().write.assert_called_once_with(dummyContent)


if (__name__ == "__main__"):
    unittest.main()
