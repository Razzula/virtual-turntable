
"""Handler class for the model."""
import json
import os
from typing import Dict, Final, Union

import torch
import torch.nn as nn
from PIL import Image

from modelling.models.ModelType import ModelType
from modelling.models.Ouroboros import Ouroboros, transform


class ModelHandler:
    """Handler class for the model."""

    def __init__(self, rootPath: str, modelsPath: str) -> None:
        """Initialise the model handler."""
        self.ROOT_DIR: Final = rootPath
        self.MODELS_PATH: Final = modelsPath

        self.model: nn.Module | None = None
        self.classes: dict[str, dict[str, str]] = {}


    def loadModel(self, modelType: ModelType, modelName: str) -> None:
        """Load a pre-trained model."""
        try:
            modelTypeName = modelType.name
        except AttributeError:
            modelTypeName = modelType

        modelPath = os.path.join(self.MODELS_PATH, modelTypeName, modelName)
        if (not os.path.exists(modelPath)):
            raise FileNotFoundError(f'Model ({modelPath}) not found.')

        checkpoint = torch.load(modelPath)

        match (modelType):
            case ModelType.OUROBOROS:
                self.model = Ouroboros(classes=checkpoint['classes']) # artificial IDs
            case _:
                raise TypeError(f'Model type ({modelTypeName}) not found.')
        if (self.model is None):
            raise RuntimeError('Model not loaded.')

        self.model.load_state_dict(checkpoint['modelStateDict'])
        self.model.eval()

        CLASS_MANIFEST: Final = os.path.join(self.ROOT_DIR, '..', 'modelling', 'data', 'manifest.json')
        if (not os.path.exists(CLASS_MANIFEST)):
            raise FileNotFoundError('No class manifest found.')
        with open(CLASS_MANIFEST, 'r', encoding='utf-8') as f:
            self.classes = json.load(f) # structured metadata


    def scan(self, imagePath: str) -> dict[str, str | int | float]:
        """Scan an image and predict the class."""

        if (self.model is None):
            raise Exception('No model loaded.')

        if (os.path.isdir(imagePath)):
            # scan dir
            results = []
            for file in sorted(os.listdir(imagePath)):
                filePath = os.path.join(imagePath, file)
                if (os.path.isfile(filePath) and file.lower().endswith(('.png', '.jpg', '.jpeg'))):
                    results.append(self._predictImage(filePath))
            return results
        elif (os.path.isfile(imagePath)):
            return [self._predictImage(imagePath)]
        else:
            raise FileNotFoundError(f"Path '{imagePath}' does not exist.")

    def _predictImage(self, imagePath: str) -> Dict[str, Union[str, int, float]]:
        """Helper function to predict the class of a single image."""

        testImage = Image.open(imagePath).convert('RGB')
        testImage = transform(testImage).unsqueeze(0)  # add batch dimension

        with torch.no_grad():
            OUTPUTS: Final = self.model(testImage)
            PROBABILITES: Final = torch.nn.functional.softmax(OUTPUTS, dim=1)
            PREDICTED_PROB, PREDICTED_CLASS = torch.max(PROBABILITES, 1)

        result = {
            'image': os.path.basename(imagePath),
            'predictedClass': self.model.classes[int(PREDICTED_CLASS.item())],
            'predictedProb': PREDICTED_PROB.item()
        }
        
        print(f"Predicted: {result['predictedClass']} ({result['predictedProb']}) for {result['image']}")
        return result
