"""A ResNet-based image classification model."""
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

class Ouroboros(nn.Module):
    """
    This neural network utilises a pretrained ResNet-18 model.
    It leverages the ResNet-18 architecture to extract features from images,
    ultimately learning the 'ID' of the image (albumName_artistName).
    """

    name: Final[str] = ModelType.OUROBOROS.value

    def __init__(self, numClasses: int, numLayers: int = 1) -> None:
        super(Ouroboros, self).__init__()

        # Load a ResNet-18 model pretrained on ImageNet
        weights = models.ResNet18_Weights.IMAGENET1K_V1
        self.resnet = models.resnet18(weights=weights)

        # This is the architecture of the neural network.
        # conv1 -> bn1 -> relu -> maxpool -> layer1 -> layer2 -> layer3 -> layer4 -> avgpool -> fc

        # Freeze all layers initially
        for param in self.resnet.parameters():
            param.requires_grad = False

        # Replace the final fully connected layer to match the number of classes in dataset
        inFeatures = self.resnet.fc.in_features
        self.resnet.fc = nn.Linear(inFeatures, numClasses)

        # Unfreeze later layers based on the desired level of fine-tuning.
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Pass the input through the network."""
        return self.resnet(x)

def trainOuro(
    model: Ouroboros,
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

        for images, labels in trainLoader:
            optimiser.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            if (torch.isnan(loss)):
                print('Early stopping triggered! (Training loss is NaN!)')
                return float('inf')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0) # prevent exploding gradients
            optimiser.step()

            runningLoss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        trainLoss = runningLoss / len(trainLoader)
        trainAccuracy = correct / total

        # Validation phase
        model.eval()
        valLoss = 0.0
        valCorrect, valTotal = 0, 0

        with torch.no_grad():
            for images, labels in validationLoader:
                outputs = model(images)
                loss = criterion(outputs, labels)
                valLoss += loss.item()

                _, predicted = torch.max(outputs, 1)
                valTotal += labels.size(0)
                valCorrect += (predicted == labels).sum().item()

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


def validateOuro(
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

    allTrueLabels = []
    allPredLabels = []

    validationLoader = DataLoader(dataset, batch_size=8, shuffle=False)

    with torch.no_grad():
        for images, trueLabels in validationLoader:
            outputs = model(images)
            predictedClasses = outputs.argmax(dim=1)

            allTrueLabels.extend(trueLabels.cpu().numpy())
            allPredLabels.extend(predictedClasses.cpu().numpy())

    # Compute confusion matrix and F1-score
    confMatrix = confusion_matrix(allTrueLabels, allPredLabels)
    f1 = f1_score(allTrueLabels, allPredLabels, average='weighted')  # Weighted handles class imbalance

    if (printResults):
        print("Confusion Matrix:\n", confMatrix)
        print(f"F1 Score: {f1:.4f}")

    return f1
