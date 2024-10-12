"""A script to train the SimpleCNN model."""
import os
from typing import Final

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
from PIL import Image

from SimpleCNN import SimpleCNN, transform

def train(model: nn.Module, trainLoader: DataLoader, criterion: nn.CrossEntropyLoss, optimiser: optim.Optimizer, epochs: int = 5) -> None:
    """_summary_

    Args:
        model (_type_): _description_
        trainLoader (_type_): _description_
        criterion (_type_): _description_
        optimiser (_type_): _description_
        epochs (int, optional): _description_. Defaults to 5.
    """

    # EPOCH LOOP
    # an epoch is a complete pass through the dataset
    # we do this several times, to allow the model to learn
    for epoch in range(epochs):

        model.train() # set the model to training mode (this is necessary for dropout and batch normalisation)

        # initialsie some statistic-trackers
        runningLoss = 0.0 # cumulative loss
        correct, total = 0, 0 # correct predictions, total predictions

        # TRAINING LOOP
        for images, labels in trainLoader:
            optimiser.zero_grad() # prevent accumulated gradients from previous iterations overflowing

            # FORWARD PASS
            # pass the images into the model, producing a prediction
            outputs = model(images)

            # COMPUTE LOSS
            # compare the model's predictions to the true labels
            loss = criterion(outputs, labels)

            # BACKPROPAGATION
            # compute the gradients of the loss, with respect to the model's parameters/weights
            loss.backward()
            # and update the model's weights accordingly
            optimiser.step()

            # track stats
            runningLoss += loss.item()
            _, predicted = torch.max(outputs, 1)

            total += labels.size(0)
            correct += (predicted == labels).sum().item()
        print(f'(Epoch {epoch+1}) Loss: {runningLoss/len(trainLoader)}\t Accuracy: {correct/total}')

# CONFIG
MODEL_NAME: Final = 'simpleCNN'

# LOAD DATASET
rootDir = os.path.dirname(os.path.abspath(__file__))
dataDir = os.path.join(rootDir, '..', 'data', 'art')
dataSet = ImageFolder(root=dataDir, transform=transform) # load each subdirectory as a class

# TODO: SPLIT DATA
trainLoader = DataLoader(dataSet, batch_size=8, shuffle=True)

# CREATE MODEL
model = SimpleCNN(classes=dataSet.classes)

# LOSS FUNCTION
# used to compute the error between the model's predictions and the true labels
criterion = nn.CrossEntropyLoss()

# OPTIMISER
# updates the model's weights, based on gradients
optimiser = optim.Adam(model.parameters(), lr=0.001)

train(model, trainLoader, criterion, optimiser, epochs=5)

# SAVE THE MODEL
torch.save(
    {
        'modelStateDict': model.state_dict(),
        'classes': model.classes
    },
    os.path.join(rootDir, 'bin', f'{MODEL_NAME}.pth')
)
