import os

from torch.utils.data import Dataset
import torchvision.transforms as transforms
from PIL import Image
import torch

def getLabelIndex(indexes: dict[str, int], albumID: str) -> int:
    """Get the index of the album in the dataset."""
    if (albumID not in indexes):
        indexes[albumID] = len(indexes)
    return indexes[albumID]

class CustomDataset(Dataset):
    def __init__(self, rootDirs: list[str], albumIndexes: dict[str, int], transform: transforms.Compose = None) -> None:
        """
        Custom dataset to provide both album and artist labels.

        Args:
            rootDir (str): Root directory containing the data.
            transform: Image transformations to apply.
        """
        self.rootDirs = rootDirs
        self.transform = transform
        self.data = []  # List of tuples (image_path, album_label)
        self.albumLabels = {}  # Mapping from album ID to index
        self.reverseAlbumLabels = {}  # Reverse mapping from index to album ID
        self.albumIndexes = albumIndexes
        self._prepareDataset()

    def _prepareDataset(self) -> None:
        """
        Prepares the dataset by mapping images to album and artist labels.
        """

        for rootDir in self.rootDirs:

            for artistName in os.listdir(rootDir):
                artistPath = os.path.join(rootDir, artistName)
                if os.path.isdir(artistPath):

                    for albumName in os.listdir(artistPath):
                        albumPath = os.path.join(artistPath, albumName)
                        if (os.path.isdir(albumPath)):
                            # Assign a unique label to each album
                            albumID = f"{artistName}/{albumName}"
                            if (albumID not in self.albumLabels):
                                albumIndex = getLabelIndex(self.albumIndexes, albumID)
                                self.albumLabels[albumID] = albumIndex
                                self.reverseAlbumLabels[albumIndex] = albumID

                            for imgName in os.listdir(albumPath):
                                imgPath = os.path.join(albumPath, imgName)
                                if (imgPath.endswith(('.png', '.jpg', '.jpeg'))):
                                    self.data.append((
                                        imgPath,
                                        self.albumLabels[albumID]
                                    ))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> tuple[Image.Image, str]:
        imgPath, albumLabel = self.data[idx]
        image = Image.open(imgPath).convert('RGB')  # Ensure RGB format
        if (not isinstance(image, torch.Tensor) and self.transform):
            image = self.transform(image)
        return image, albumLabel


class CustomDataset2(Dataset):
    def __init__(self,
        rootDirs: list[str],
        albumIndexes: dict[str, int], artistIndexes: dict[str, int],
        transform: transforms.Compose = None,
    ) -> None:
        """
        Custom dataset to provide both album and artist labels.

        Args:
            rootDir (str): Root directory containing the data.
            transform: Image transformations to apply.
        """
        self.rootDirs = rootDirs
        self.transform = transform

        self.data = []  # List of tuples (image_path, album_label)
        self.albumLabels = {}  # Mapping from album ID to index
        self.reverseAlbumLabels = {}  # Reverse mapping from index to album ID
        self.artistLabels = {}  # Mapping from artist ID to index
        self.reverseArtistLabels = {}  # Reverse mapping from index to artist ID

        self.albumIndexes = albumIndexes
        self.artistIndexes = artistIndexes

        self._prepareDataset()

    def _prepareDataset(self) -> None:
        """
        Prepares the dataset by mapping images to album and artist labels.
        """

        for rootDir in self.rootDirs:

            for artistName in os.listdir(rootDir):
                artistPath = os.path.join(rootDir, artistName)
                if os.path.isdir(artistPath):

                    # Assign a unique label to each artist
                    if (artistName not in self.artistLabels):
                        artistIndex = getLabelIndex(self.artistIndexes, artistName)
                        self.artistLabels[artistName] = artistIndex
                        self.reverseArtistLabels[artistIndex] = artistName

                    for albumName in os.listdir(artistPath):
                        albumPath = os.path.join(artistPath, albumName)
                        if (os.path.isdir(albumPath)):
                            # Assign a unique label to each album
                            albumID = f"{artistName}/{albumName}"
                            if (albumID not in self.albumLabels):
                                albumIndex = getLabelIndex(self.albumIndexes, albumID)
                                self.albumLabels[albumID] = albumIndex
                                self.reverseAlbumLabels[albumIndex] = albumID

                            for imgName in os.listdir(albumPath):
                                imgPath = os.path.join(albumPath, imgName)
                                if (imgPath.endswith(('.png', '.jpg', '.jpeg'))):
                                    self.data.append((
                                        imgPath,
                                        self.albumLabels[albumID],
                                        self.artistLabels[artistName]
                                    ))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> tuple[Image.Image, tuple[str, str]]:
        imgPath, albumLabel, artistLabel = self.data[idx]
        image = Image.open(imgPath).convert('RGB')  # Ensure RGB format
        if self.transform:
            image = self.transform(image)
        return image, (albumLabel, artistLabel)


class ArtificiallyAugmentedDataset():
    """Custom dataset to combine original and multiple augmentations."""

    def __init__(self,
        originalDataset: CustomDataset,
        transform: transforms.Compose, augmentTransform: transforms.Compose,
        numAugmentations: int = 4,
    ) -> None:
        self.originalDataset = originalDataset
        self.transform = transform
        self.augmentTransform = augmentTransform
        self.numAugmentations = numAugmentations

    def __len__(self) -> int:
        # original images with augmented copies
        return len(self.originalDataset) * (1 + self.numAugmentations)

    def __getitem__(self, idx: int) -> tuple[Image.Image, str]:

        originalIdx = idx // (1 + self.numAugmentations)
        image, labels = self.originalDataset[originalIdx]

        if ((idx % (1 + self.numAugmentations)) == 0):
            # Return the original image
            transformedImage = self.transform(image)
            return transformedImage, labels

        # Return an augmented image
        augmentedImage = self.augmentTransform(image)
        return augmentedImage, labels
