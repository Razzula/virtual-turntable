"""A two-headed CNN for image classification."""
from typing import Final
import os

from numpy import ndarray
import torch.nn as nn
import torchvision.models as models

from torch.utils.data import DataLoader
import torch.optim as optim
import torch.nn as nn
import torch

from sklearn.metrics import confusion_matrix, f1_score
from utils.CustomDataset import CustomDataset

from utils.ModelType import ModelType

class Amphisbaena(nn.Module):
    """
    This neural network utilises a pretrained ResNet-18 model.
    It leverages the ResNet-18 architecture to extract features from images,
    using two output heads to predict the album and artist of the image.
    """

    name: Final[str] = ModelType.AMPHISBAENA.value

    def __init__(self, numAlbums: int, numArtists: int, numLayers: int = 1):
        super().__init__()

        # Load a ResNet-18 model pretrained on ImageNet
        weights = models.ResNet18_Weights.IMAGENET1K_V1
        self.resnet = models.resnet18(weights=weights)

        # This is the architecture of the neural network.
        # conv1 -> bn1 -> relu -> maxpool -> layer1 -> layer2 -> layer3 -> layer4 -> avgpool -> fc

        # Freeze early layers
        for param in self.resnet.parameters():
            param.requires_grad = False

        # Get input features of original FC layer
        inFeatures = self.resnet.fc.in_features

        # Remove the original fully connected layer
        self.resnet.fc = nn.Identity()

        # Define two new output heads
        self.albumHead = nn.Linear(inFeatures, numAlbums)
        self.artistHead = nn.Linear(inFeatures, numArtists)

        # Unfreeze selected layers for fine-tuning
        if (numLayers >= 1):
            for param in self.resnet.layer4.parameters():
                param.requires_grad = True
        if (numLayers >= 2):
            for param in self.resnet.layer3.parameters():
                param.requires_grad = True
        if (numLayers >= 3):
            for param in self.resnet.layer2.parameters():
                param.requires_grad = True
        if (numLayers >= 4):
            for param in self.resnet.layer1.parameters():
                param.requires_grad = True

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Pass the input through the network."""
        x = self.resnet(x)
        albumOut = self.albumHead(x)
        artistOut = self.artistHead(x)
        return albumOut, artistOut

def trainAmphi(
    model: Amphisbaena,
    trainLoader: DataLoader, validationLoader: DataLoader,
    maxEpochs: int = 5, learningRate: float = 1e-3, weightDecay: float = 1e-4,
    patience: int = 4, overallBestValLoss: float = float('inf'),
) -> float:
    """
    Train the model and evaluate on validation data each epoch.
    """
    print(f'\nTraining... (α={learningRate}, λ={weightDecay}, B={trainLoader.batch_size})')

    # LOSS FUNCTION
    # used to compute the error between the model's predictions and the true labels
    criterion = nn.CrossEntropyLoss()

    # OPTIMISER
    # updates the model's weights, based on gradients
    optimiser = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=learningRate, weight_decay=weightDecay,
    )

    bestValLoss = float('inf')
    epochsSinceBest = 0

    for epoch in range(maxEpochs):

        # Training phase
        model.train()
        runningLoss = 0.0
        correct, total = 0, 0

        for images, (albumLabels, artistLabels) in trainLoader:
            optimiser.zero_grad()
            albumOutputs, artistOutputs = model(images)

            albumLoss = criterion(albumOutputs, albumLabels)
            artistLoss = criterion(artistOutputs, artistLabels)
            totalLoss = albumLoss + artistLoss
            if (torch.isnan(totalLoss)):
                print('Early stopping triggered! (Training loss is NaN!)')
                return float('inf')
            totalLoss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0) # prevent exploding gradients
            optimiser.step()

            runningLoss += totalLoss.item()
            _, albumPredicted = torch.max(albumOutputs, 1)
            _, artistPredicted = torch.max(artistOutputs, 1)

            total += albumLabels.size(0) + artistLabels.size(0)
            correct += (albumPredicted == albumLabels).sum().item() + (artistPredicted == artistLabels).sum().item()

        trainLoss = runningLoss / len(trainLoader)
        trainAccuracy = correct / total

        # Validation phase
        model.eval()
        valLoss = 0.0
        valCorrect, valTotal = 0, 0

        with torch.no_grad():
            for images, (albumLabels, artistLabels) in validationLoader:
                albumOutputs, artistOutputs = model(images)

                albumLoss = criterion(albumOutputs, albumLabels)
                artistLoss = criterion(artistOutputs, artistLabels)
                totalLoss = albumLoss + artistLoss

                valLoss += totalLoss.item()

                _, albumPredicted = torch.max(albumOutputs, 1)
                _, artistPredicted = torch.max(artistOutputs, 1)

                valTotal += albumLabels.size(0) + artistLabels.size(0)
                valCorrect += (albumPredicted == albumLabels).sum().item() + (artistPredicted == artistLabels).sum().item()

        valLoss /= len(validationLoader)
        valAccuracy = valCorrect / valTotal

        print(
            f"(Epoch {epoch+1}) "
            f"Train Loss: {trainLoss:.4f}, Train Accuracy: {trainAccuracy:.4f} || "
            f"Val Loss: {valLoss:.4f}, Val Accuracy: {valAccuracy:.4f}"
        )

        # early stopping
        if (valLoss < bestValLoss):
            bestValLoss = valLoss
            epochsSinceBest = 0

            if (valLoss < overallBestValLoss):
                overallBestValLoss = valLoss
                rootDir = os.path.dirname(os.path.abspath(__file__))
                torch.save({
                    'epoch': epoch + 1,
                    'modelStateDict': model.state_dict(),
                    'optimiserStateDict': optimiser.state_dict(),
                    'valLoss': valLoss,
                }, os.path.join(rootDir, 'bin', f'{model.name}-checkpoint.pt'))
        else:
            epochsSinceBest += 1

        if (epochsSinceBest >= patience):
            print('Early stopping triggered!')
            break

    return overallBestValLoss

def validateAmphi(
    model: torch.nn.Module, dataset: CustomDataset, printResults: bool = False
) -> float | ndarray:
    """
    Validates the entire dataset using the given model.

    Args:
        model (torch.nn.Module): The trained model to use for validation.
        dataset (CustomDataset): The dataset to validate.
        printResults (bool): Whether to print the results or not.

    Returns:
        dict: A dictionary mapping album IDs to a list of (true_label, predicted_label, confidence).
    """
    model.eval()

    allTrueAlbums, allPredAlbums = [], []
    allTrueArtists, allPredArtists = [], []

    validationLoader = DataLoader(dataset, batch_size=8, shuffle=False)

    with torch.no_grad():
        for images, (trueAlbums, trueArtists) in validationLoader:  # Expecting tuple (album, artist)
            albumOut, artistOut = model(images)

            predAlbums = albumOut.argmax(dim=1)
            predArtists = artistOut.argmax(dim=1)

            allTrueAlbums.extend(trueAlbums.cpu().numpy())
            allPredAlbums.extend(predAlbums.cpu().numpy())

            allTrueArtists.extend(trueArtists.cpu().numpy())
            allPredArtists.extend(predArtists.cpu().numpy())

    # Compute confusion matrices and F1-scores
    albumConfMatrix = confusion_matrix(allTrueAlbums, allPredAlbums)
    artistConfMatrix = confusion_matrix(allTrueArtists, allPredArtists)

    albumF1 = f1_score(allTrueAlbums, allPredAlbums, average='weighted')
    artistF1 = f1_score(allTrueArtists, allPredArtists, average='weighted')

    if (printResults):
        print("Album Confusion Matrix:\n", albumConfMatrix)
        print(f"Album F1 Score: {albumF1:.4f}")
        print("\nArtist Confusion Matrix:\n", artistConfMatrix)
        print(f"Artist F1 Score: {artistF1:.4f}")

    return (albumF1 + artistF1) / 2
