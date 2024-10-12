
"""Handler class for the model."""
import os
from typing import Final

import torch
import torch.nn as nn
from PIL import Image

from modelling.models.SimpleCNN import SimpleCNN, transform

class ModelHandler:
    """Handler class for the model."""

    def __init__(self, modelPath: str | None = None) -> None:
        """Initialise the model handler."""
        self.model: nn.Module | None = None

        if (modelPath is not None):
            self.loadModel(modelPath)


    def loadModel(self, modelPath: str) -> None:
        """Load a pre-trained model."""
        checkpoint = torch.load(modelPath)
        self.model = SimpleCNN(classes=checkpoint['classes'])
        self.model.load_state_dict(checkpoint['modelStateDict'])
        self.model.eval()


    def scan(self, imagePath: str) -> dict[str, str | int | float]:
        """Scan an image and predict the class."""

        if (self.model is None):
            raise Exception('No model loaded.')

        testImage = Image.open(imagePath)
        testImage = transform(testImage).unsqueeze(0)  # add batch dimension

        with torch.no_grad():
            OUTPUTS: Final = self.model(testImage)
            PROBABILITES: Final = torch.nn.functional.softmax(OUTPUTS, dim=1)
            PREDICTED_PROB, PREDICTED_CLASS = torch.max(PROBABILITES, 1)

        print(f'Predicted: {self.model.classes[int(PREDICTED_CLASS.item())]} ({PREDICTED_PROB.item()})')

        return {
            'predictedClass': self.model.classes[int(PREDICTED_CLASS.item())],
            'predictedProb': PREDICTED_PROB.item()
        }
