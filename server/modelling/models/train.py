"""A script to train the SimpleCNN model."""
import json
import os
from typing import Final

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader

from BabyOuroboros import BabyOuroboros
from Ouroboros import Ouroboros, trainOuro, validateOuro
from Amphisbaena import Amphisbaena
from utils.ModelType import ModelType
from utils.Transforms import globalTransformer, augmentedTransforms
from utils.CustomDataset import CustomDataset, CustomDataset2, ArtificiallyAugmentedDataset

# CONFIG
MODEL_NAME: Final = ModelType.BABY_OUROBOROS

ALPHA: Final = 1e-3
LAMBDA: Final = 1e-4
BATCH_SIZE: Final = 32
MAX_EPOCHS: Final = 5
NUM_AUGMENTATIONS: Final = 5
UNFREEZE_LAYERS: Final = 2

albumIndexes = {}
artistIndexes = {}

# LOAD DATASET(S)
rootDir = os.path.dirname(os.path.abspath(__file__))
dataDir = os.path.join(rootDir, '..', 'data')

trainDirs = [
    os.path.join(dataDir, 'art_'),
    os.path.join(dataDir, 'art_a_dig'),
    os.path.join(dataDir, 'art_b_phys'),
    os.path.join(dataDir, 'art_c_dig'),
]
if (MODEL_NAME == ModelType.AMPHISBAENA):
    # the Amphisbaena model requires two label sets
    vanillaDataset = CustomDataset2(trainDirs, albumIndexes, artistIndexes, transform=globalTransformer)
else:
    # the Ouroboros models only require one label set
    vanillaDataset = CustomDataset(trainDirs, albumIndexes, transform=globalTransformer)
dataset = ArtificiallyAugmentedDataset(vanillaDataset, augmentedTransforms, numAugmentations=4)

valDirs = [
    os.path.join(dataDir, 'art_c_phys'),
]
valDataset = CustomDataset(rootDirs=valDirs, transform=globalTransformer)

testDirs = [
    os.path.join(dataDir, 'art_c_phys'),
    os.path.join(dataDir, 'art_x'),
]
testDataset = CustomDataset(rootDirs=testDirs, transform=globalTransformer)

# VERIFY DATASET INTREGRITY
with open(os.path.join(dataDir, 'manifest.json'), 'r', encoding='utf-8') as f:
    trueClasses = json.load(f)

error = False
for i in range(len(dataset)):
    try:
        img, label = dataset[i]
    except OSError as e:
        error = True
        print(trueClasses[dataset.albumLabels[label + 1]])
if (error):
    raise FileNotFoundError('Dataset is corrupted')

# SPLIT and LOAD DATA
trainLoader = DataLoader(dataset, batch_size=8, shuffle=True)
validationLoader = DataLoader(valDataset, batch_size=8, shuffle=True)

# CREATE MODEL
if (MODEL_NAME == ModelType.BABY_OUROBOROS):
    model = BabyOuroboros(classes=dataset.classes)
elif (MODEL_NAME == ModelType.OUROBOROS):
    model = Ouroboros(classes=dataset.classes, numLayers=UNFREEZE_LAYERS)
elif (MODEL_NAME == ModelType.AMPHISBAENA):
    model = Amphisbaena(classes=dataset.classes, numLayers=UNFREEZE_LAYERS)
else:
    raise ValueError(f'Invalid model type: {MODEL_NAME}')

if (MODEL_NAME == ModelType.AMPHISBAENA):
    # the Amphisbaena model requires two label sets
    raise NotImplementedError
else:
    # the Ouroboros models only require one label set
    trainOuro(
        model=model,
        trainLoader=trainLoader, validationLoader=validationLoader,
        maxEpochs=MAX_EPOCHS, learningRate=ALPHA, weightDecay=LAMBDA,
        patience=4,
    )

# LOAD MODEL FROM CHECKPOINT
model = torch.load(os.path.join(rootDir, 'bin', f'{MODEL_NAME.value}-checkpoint.pt'))

# EVALUATE MODEL
if (MODEL_NAME == ModelType.AMPHISBAENA):
    # the Amphisbaena model requires two label sets
    raise NotImplementedError
else:
    # the Ouroboros models only require one label set
    validateOuro(model, valDataset, printResults=True)
    validateOuro(model, testDataset, printResults=True)

# SAVE THE MODEL
torch.save(
    {
        'modelStateDict': model.state_dict(),
        'classes': model.classes,
    },
    os.path.join(rootDir, 'bin', f'{MODEL_NAME.value}.pth')
)
