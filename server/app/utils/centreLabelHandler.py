"""Handler class for the centre labels."""
import os
from typing import Any, Final

from fastapi import HTTPException

import cv2
import numpy as np

from app.utils.discogsAPI import DiscogsAPI

def detectCircle(imagePath: str) -> np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]]:
    """TODO"""
    image = cv2.imread(imagePath)

    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grey, (15, 15), 0)

    # Detect circles
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.5, minDist=100, param1=80, param2=80, minRadius=200, maxRadius=0)
    return circles

def cropLabel(imagePath: str) -> np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]] | None:
    """TODO"""
    circles = detectCircle(imagePath)
    pass
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
    """TODO"""
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

    def getCandidates(self, albumName: str, artistName: str | None, year: str | None, medium: str | None) -> Any | None:
        """Get the candidate centre labels."""

        candidatesDir = os.path.join(self.DATA_DIR, 'centreLabelCandidates')

        # clear existing candidates
        for file in os.listdir(candidatesDir):
            os.remove(os.path.join(candidatesDir, file))

        # download from Discogs
        album = self.DISCOGS_API.searchRelease(albumName, artistName, year, medium)
        if (album is not None):
            images, metadata = self.DISCOGS_API.getReleaseData(album['id'])
            if (images is None or len(images) == 0):
                raise HTTPException(status_code=404, detail='Failed to find images for album')
            for (index, image) in enumerate(images):
                url = image['uri']
                self.DISCOGS_API.downloadImage(url, os.path.join(candidatesDir, f'{album["id"]}({index}).png'))
            return metadata
        else:
            raise HTTPException(status_code=404, detail='Failed to find album on Discogs.')

    def serveCentreLabel(self, albumID: str, albumName: str, artistName: str | None, year: str | None, medium: str | None) -> Any | None:
        """Serve the centre label for the given album."""

        metadata = self.getCandidates(albumName, artistName, year, medium)

        centreLabel = processImages(os.path.join(self.DATA_DIR, 'centreLabelCandidates'))
        if (centreLabel is not None):
            # store as file:
            #   1. to serve to client
            #   2. for persistent caching
            cv2.imwrite(os.path.join(self.DATA_DIR, 'centreLabels', f'{albumID}.png'), centreLabel)
            return metadata
        return None # failed
