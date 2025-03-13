"""A simple CNN for image classification."""
from typing import List

import torch
import torch.nn as nn

class BabyOuroboros(nn.Module):
    """
    This is a simple convolutional neural network, for POC.
    It has two convolutional layers and two fully connected layers (see below).
    It effectively learns the 'ID' of the image (albumName_artistName).
    """

    classes: List[str] = []

    def __init__(self, classes: List[str]) -> None:
        super(BabyOuroboros, self).__init__()

        self.classes = classes
        numClasses = len(classes)

        # This is the architecture of the neural network.
        # It is composed of two convolutional layers and two fully connected layers.
        # conv1 -> pool -> conv2 -> pool -> fc1 -> fc2

        # CONVOLUTIONAL LAYER 1
        self.conv1 = nn.Conv2d(
            3, # 3 channels (RBG)
            32, # 32 output filters (feature maps)
            kernel_size=3, # each filter will scan 3x3 patches of the image
            stride=1, # each filter will move 1 pixel at a time
            padding=1 # the input is padded, to esnure the output is the same size as the input
        )

        # MAX-POOLING LAYER
        # reduces spatial dimensions of the input feature maps
        # this reduces the number of parameters and computations in the network
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)

        # CONVOLUTIONAL LAYER 2
        # the 32 feature maps are now fed into a second layer, resulting in 64 output filters
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)

        # FULLY CONNECTED LAYER 1
        self.fc1 = nn.Linear(
            64 * 56 * 56, # 64 feature maps, each 56x56 pixels
            128 # 128 output neurons
        )

        # FULLY CONNECTED LAYER 2
        # this layer outputs logits (raw scores) for each class
        self.fc2 = nn.Linear(128, numClasses)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """_summary_

        Args:
            x (_type_): _description_

        Returns:
            _type_: _description_
        """

        # pool the first convolutional layer
        # the size of the feature maps are halved
        x = self.pool(
            # apply the ReLU activation function
            # this introduces non-linearity to the model
            torch.relu(
                # apply the first convolutional layer
                # the 32 filters are applied to the input image
                self.conv1(x)
            )
        )

        # pool the second convolutional layer
        x = self.pool(torch.relu(self.conv2(x)))

        # flatten the feature maps
        x = x.view(-1, 64 * 56 * 56)

        # fully-connected layers
        x = torch.relu(self.fc1(x))
        x = self.fc2(x) # no activation function, as this is handled by the loss function

        return x
