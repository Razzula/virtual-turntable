"""Handler class for the centre labels."""
import os
from typing import Any, Final

import cv2
import numpy as np
from fastapi import HTTPException

from app.APIs.discogsAPI import DiscogsAPI


def detectCircle(imagePath: str) -> np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]]:
    """Detect circle within an image."""
    image = cv2.imread(imagePath)

    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grey, (15, 15), 0)

    # Detect circles
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT,
        dp=1.5, minDist=100,
        param1=80, param2=80,
        minRadius=200, maxRadius=0
    )
    return circles

def cropLabel(imagePath: str) -> np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]] | None:
    """Crop the current image to the largest circle detected."""
    circles = detectCircle(imagePath)
    if (circles is not None):
        image = cv2.imread(imagePath)
        circles = np.round(circles[0, :]).astype("int")

        for (x, y, r) in circles:
            x1 = max(x - r, 0)
            y1 = max(y - r, 0)
            x2 = min(x + r, image.shape[1])
            y2 = min(y + r, image.shape[0])

            cropped = image[y1:y2, x1:x2]
            return cropped
    return None

def processImages(directory: str) -> np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]] | None:
    """Process the images in the given directory, returning the best selection."""
    for file in os.listdir(directory):
        imagePath = os.path.join(directory, file)
        cropped = cropLabel(imagePath)
        if (cropped is not None):
            return cropped
    return None

class CentreLabelHandler:
    """Handler class for the centre labels."""

    def __init__(self, dataPath: str, discogsAPI: DiscogsAPI) -> None:
        """Initialise the centre labels."""
        self.DATA_DIR: Final = dataPath
        self.DISCOGS_API: Final = discogsAPI

        for subDir in ['centreLabels', 'centreLabelCandidates']:
            if (not os.path.exists(os.path.join(dataPath, subDir))):
                os.makedirs(os.path.join(dataPath, subDir))

    def findReleaseData(self, albumName: str, artistName: str | None, year: str | None, medium: str | None) -> Any | None:
        """Find the release data for the given album."""
        album = self.DISCOGS_API.searchRelease(albumName, artistName, year, medium)
        if (album is not None):
            return self.DISCOGS_API.getDataForRelease(album['id'])
        else:
            raise HTTPException(status_code=404, detail='Failed to find album on Discogs.')

    def downloadCandidates(self, albumID: str, images: list[Any]) -> None:
        """Download images for an album."""

        candidatesDir = os.path.join(self.DATA_DIR, 'centreLabelCandidates')

        # clear existing candidates
        for file in os.listdir(candidatesDir):
            os.remove(os.path.join(candidatesDir, file))

        for (index, image) in enumerate(images):
            url = image['uri']
            self.DISCOGS_API.downloadImage(url, os.path.join(candidatesDir, f'{albumID}({index}).png'))

    def getCandidates(self, albumName: str, artistName: str | None, year: str | None, medium: str | None) -> None:
        """Get the candidate centre labels."""

        # download from Discogs
        album = self.DISCOGS_API.searchRelease(albumName, artistName, year, medium)
        if (album is not None):
            images, _ = self.DISCOGS_API.getDataForRelease(album['id'])
            if (images is None or len(images) == 0):
                raise HTTPException(status_code=404, detail='Failed to find images for album')
            self.downloadCandidates(album['id'], images)
        else:
            raise HTTPException(status_code=404, detail='Failed to find album on Discogs.')

    def serveCentreLabel(self, albumID: str, albumName: str | None = None, artistName: str | None = None, year: str | None = None, medium: str | None = None, images: Any = None) -> bool:
        """Serve the centre label for the given album."""

        if (images is None):
            if (albumName is None):
                raise HTTPException(status_code=400, detail='No album name provided.')
            self.getCandidates(albumName, artistName, year, medium)
        else:
            self.downloadCandidates(albumID, images)

        centreLabel = processImages(os.path.join(self.DATA_DIR, 'centreLabelCandidates'))
        if (centreLabel is not None):
            # store as file:
            #   1. to serve to client
            #   2. for persistent caching
            cv2.imwrite(os.path.join(self.DATA_DIR, 'centreLabels', f'{albumID}.png'), centreLabel)
            return True
        return False # failed
