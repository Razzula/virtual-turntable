"""Test suite for the CentreLabelHandler class and its utility functions."""
import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from app.modules.centreLabelHandler import (
    detectCircle,
    cropLabel,
    processImages,
    CentreLabelHandler,
)
from app.APIs.DiscogsAPI import DiscogsAPI  # Dummy discogs API for testing


# --- Tests for utility functions ---

class TestImageProcessingUtils(unittest.TestCase):
    """Test suite for image processing utility functions."""

    @patch("app.modules.centreLabelHandler.cv2.HoughCircles")
    @patch("app.modules.centreLabelHandler.cv2.GaussianBlur")
    @patch("app.modules.centreLabelHandler.cv2.cvtColor")
    @patch("app.modules.centreLabelHandler.cv2.imread")
    def test_detectCircle(self, mockImread: Any, mockCvtColor: Any, mockBlur: Any, mockHough: Any) -> None:
        """Test detectCircle returns detected circles."""
        # Create dummy image (e.g. 500x500 with 3 channels)
        dummyImage: np.ndarray = np.zeros((500, 500, 3), dtype=np.uint8)
        mockImread.return_value = dummyImage
        dummyGrey: np.ndarray = np.zeros((500, 500), dtype=np.uint8)
        mockCvtColor.return_value = dummyGrey
        dummyBlurred: np.ndarray = np.zeros((500, 500), dtype=np.uint8)
        mockBlur.return_value = dummyBlurred
        dummyCircles: np.ndarray = np.array([[[250, 250, 100]]])
        mockHough.return_value = dummyCircles

        circles: Optional[np.ndarray] = detectCircle("dummy.jpg")
        self.assertIsNotNone(circles)
        self.assertTrue((circles == dummyCircles).all())

    @patch("app.modules.centreLabelHandler.detectCircle")
    @patch("app.modules.centreLabelHandler.cv2.imread")
    def test_cropLabel(self, mockImread: Any, mockDetect: Any) -> None:
        """Test cropLabel returns a cropped image when a circle is detected."""
        # Prepare a dummy circle: one circle at (100, 100) with radius 50.
        dummyCircles: np.ndarray = np.array([[[100, 100, 50]]])
        mockDetect.return_value = dummyCircles

        # Create a dummy image: 200x200 pixels with three channels.
        dummyImage: np.ndarray = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        mockImread.return_value = dummyImage

        cropped: Optional[np.ndarray] = cropLabel("dummy.jpg")
        self.assertIsNotNone(cropped)
        # The cropped region should be from (50,50) to (150,150)
        expected: np.ndarray = dummyImage[50:150, 50:150]
        self.assertTrue(np.array_equal(cropped, expected))

    def test_processImages(self) -> None:
        """Test processImages returns the first candidate crop in a directory."""
        with tempfile.TemporaryDirectory() as tmpDir:
            # Create two dummy image files.
            fileNames: List[str] = ["a.jpg", "b.png"]
            for fileName in fileNames:
                filePath: str = os.path.join(tmpDir, fileName)
                with open(filePath, "wb") as f:
                    f.write(b"dummy data")
            # Patch cropLabel to return a dummy crop when called.
            with patch("app.modules.centreLabelHandler.cropLabel", return_value=np.array([[1, 2], [3, 4]])) as mockCrop:
                result: Optional[np.ndarray] = processImages(tmpDir)
                self.assertIsNotNone(result)
                self.assertTrue((result == np.array([[1, 2], [3, 4]])).all())
                # Ensure cropLabel was called for at least one file.
                self.assertGreaterEqual(mockCrop.call_count, 1)


# --- Tests for CentreLabelHandler class ---

class TestCentreLabelHandler(unittest.TestCase):
    """Test suite for the CentreLabelHandler class."""

    def setUp(self) -> None:
        """Set up a temporary data directory and a dummy DiscogsAPI for testing."""
        self.tempDir: str = tempfile.mkdtemp(prefix="data_")
        # Create a dummy DiscogsAPI using MagicMock.
        self.dummyDiscogs: DiscogsAPI = MagicMock(spec=DiscogsAPI)
        # Instantiate CentreLabelHandler; its __init__ creates required subdirectories.
        self.handler: CentreLabelHandler = CentreLabelHandler(self.tempDir, self.dummyDiscogs)

    def tearDown(self) -> None:
        """Remove temporary directories after tests."""
        import shutil

        shutil.rmtree(self.tempDir, ignore_errors=True)

    def test_directoriesCreated(self) -> None:
        """Test that required subdirectories are created on initialisation."""
        centreLabelsDir: str = os.path.join(self.tempDir, "centreLabels")
        candidatesDir: str = os.path.join(self.tempDir, "centreLabelCandidates")
        self.assertTrue(os.path.exists(centreLabelsDir))
        self.assertTrue(os.path.exists(candidatesDir))

    def test_findReleaseData_success(self) -> None:
        """Test findReleaseData returns release data when DiscogsAPI returns album data."""
        # Dummy album returned from searchRelease.
        dummyAlbum: Dict[str, str] = {"id": "12345"}
        self.dummyDiscogs.searchRelease.return_value = dummyAlbum
        # Dummy release data from getDataForRelease.
        dummyData: Any = {"images": [{"uri": "http://example.com/img.jpg"}], "metadata": {}}
        self.dummyDiscogs.getDataForRelease.return_value = dummyData

        result: Any = self.handler.findReleaseData("Album", "Artist", "2020", "Vinyl")
        self.assertEqual(result, dummyData)
        self.dummyDiscogs.searchRelease.assert_called_once()
        self.dummyDiscogs.getDataForRelease.assert_called_once_with(dummyAlbum["id"])

    def test_findReleaseData_failure(self) -> None:
        """Test findReleaseData raises HTTPException when no album is found."""
        self.dummyDiscogs.searchRelease.return_value = None
        with self.assertRaises(HTTPException) as context:
            self.handler.findReleaseData("Album", "Artist", "2020", "Vinyl")
        self.assertEqual(context.exception.status_code, 404)

    @patch("os.remove")
    @patch("os.listdir")
    def test_downloadCandidates(self, mockListdir: Any, mockRemove: Any) -> None:
        """Test downloadCandidates clears old files and downloads new candidate images."""
        # Set up a dummy list of files in the candidates directory.
        candidatesDir: str = os.path.join(self.tempDir, "centreLabelCandidates")
        mockListdir.return_value = ["old1.png", "old2.png"]
        albumID: str = "12345"
        dummyImages: List[Dict[str, Any]] = [
            {"uri": "http://example.com/img1.jpg"},
            {"uri": "http://example.com/img2.jpg"}
        ]
        self.handler.downloadCandidates(albumID, dummyImages)
        # Expect os.remove to be called for each old file.
        self.assertEqual(mockRemove.call_count, 2)
        # Verify DiscogsAPI.downloadImage called for each candidate.
        calls = [((dummyImages[i]["uri"], os.path.join(candidatesDir, f'{albumID}({i}).png')),) for i in range(len(dummyImages))]
        self.dummyDiscogs.downloadImage.assert_has_calls(calls, any_order=True)

    @patch.object(CentreLabelHandler, "downloadCandidates")
    @patch.object(CentreLabelHandler, "getCandidates")
    def test_serveCentreLabel_withImages(self, mockGetCandidates: Any, mockDownloadCandidates: Any) -> None:
        """Test serveCentreLabel downloads candidates and writes the centre label image."""
        # Simulate that processImages returns a dummy crop.
        dummyCrop: np.ndarray = np.array([[1, 2], [3, 4]])
        with patch("app.modules.centreLabelHandler.processImages", return_value=dummyCrop) as mockProcess:
            with patch("app.modules.centreLabelHandler.cv2.imwrite") as mockImwrite:
                result: bool = self.handler.serveCentreLabel("12345", images=[{"uri": "http://example.com/img.jpg"}])
                self.assertTrue(result)
                mockDownloadCandidates.assert_called_once_with("12345", [{"uri": "http://example.com/img.jpg"}])
                # Verify cv2.imwrite was called with the correct file path.
                centreLabelsDir: str = os.path.join(self.tempDir, "centreLabels")
                expectedPath: str = os.path.join(centreLabelsDir, "12345.png")
                mockImwrite.assert_called_once_with(expectedPath, dummyCrop)

    def test_serveCentreLabel_noAlbumName(self) -> None:
        """Test serveCentreLabel raises HTTPException when no albumName is provided and images is None."""
        with self.assertRaises(HTTPException) as context:
            self.handler.serveCentreLabel("12345")
        self.assertEqual(context.exception.status_code, 400)


if (__name__ == "__main__"):
    unittest.main()
