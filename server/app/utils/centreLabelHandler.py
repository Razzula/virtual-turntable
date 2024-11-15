"""Handler class for the centre labels."""
import os
from typing import Any, Final

import cv2
import numpy as np

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

    def __init__(self, dataPath: str) -> None:
        """Initialise the centre labels."""
        self.DATA_DIR: Final = dataPath

        for subDir in ['centreLabels', 'centreLabelCandidates']:
            if (not os.path.exists(os.path.join(dataPath, subDir))):
                os.makedirs(os.path.join(dataPath, subDir))

    def getCandidates(self, album: str) -> None:
        """Get the candidate centre labels."""
        pass # TODO: using Discogs API

    def serveCentreLabel(self, album: str) -> bool:
        """Serve the centre label for the given album."""

        self.getCandidates(album)

        centreLabel = processImages(os.path.join(self.DATA_DIR, 'centreLabelCandidates'))
        if (centreLabel is not None):
            cv2.imwrite(os.path.join(self.DATA_DIR, 'centreLabels', f'{album}.png'), centreLabel)
            return True
        return False
