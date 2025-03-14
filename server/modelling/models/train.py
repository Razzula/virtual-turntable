"""A script to train the SimpleCNN model."""
import json
import os
from typing import Final
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
import torchvision.transforms as transforms

from BabyOuroboros import BabyOuroboros
from Ouroboros import Ouroboros, trainOuro, validateOuro
from Amphisbaena import Amphisbaena, trainAmphi, validateAmphi
from utils.ModelType import ModelType
from utils.Transforms import globalTransforms, augmentedTransforms
from utils.CustomDataset import CustomDataset, CustomDataset2, ArtificiallyAugmentedDataset

# CONFIG
MODEL_NAME: Final = ModelType.AMPHISBAENA

ALPHA: Final = 1e-4
LAMBDA: Final = 1e-3
BATCH_SIZE: Final = 32
MAX_EPOCHS: Final = 100
NUM_AUGMENTATIONS: Final = 5
UNFREEZE_LAYERS: Final = 2

albumIndexes = {}
artistIndexes = {}

timer = time.time()

# LOAD DATASET(S)
rootDir = os.path.dirname(os.path.abspath(__file__))
dataDir = os.path.join(rootDir, '..', 'data')

globalTransformer = transforms.Compose(globalTransforms)

trainDirs = [
    os.path.join(dataDir, 'art_'),
    os.path.join(dataDir, 'art_a_dig'),
    os.path.join(dataDir, 'art_b_phys'),
    os.path.join(dataDir, 'art_c_dig'),
]
valDirs = [
    os.path.join(dataDir, 'art_c_phys'),
]
testDirs = [
    os.path.join(dataDir, 'art_c_phys'),
    os.path.join(dataDir, 'art_x'),
]

if (MODEL_NAME == ModelType.AMPHISBAENA):
    # the Amphisbaena model requires two label sets
    vanillaDataset = CustomDataset2(trainDirs, albumIndexes, artistIndexes, transform=None)
    valDataset = CustomDataset2(valDirs, albumIndexes, artistIndexes, transform=globalTransformer)
    testDataset = CustomDataset2(testDirs, albumIndexes, artistIndexes, transform=globalTransformer)
else:
    # the Ouroboros models only require one label set
    vanillaDataset = CustomDataset(trainDirs, albumIndexes, transform=None)
    valDataset = CustomDataset(valDirs, albumIndexes, transform=globalTransformer)
    testDataset = CustomDataset(testDirs, albumIndexes, transform=globalTransformer)

augmentedTransformer = transforms.Compose(globalTransforms + augmentedTransforms)
augmentedDataset = ArtificiallyAugmentedDataset(vanillaDataset, globalTransformer, augmentedTransformer, numAugmentations=5)
print(f'Loaded {len(augmentedDataset)} training samples')
print(f'Loaded {len(valDataset)} validation samples')
print(f'Loaded {len(testDataset)} test samples')


# VERIFY DATASET INTREGRITY
with open(os.path.join(dataDir, 'manifest.json'), 'r', encoding='utf-8') as f:
    trueClasses = json.load(f)

error = False
for i in range(len(augmentedDataset)):
    try:
        img, label = augmentedDataset[i]
    except OSError as e:
        error = True
        print(trueClasses[augmentedDataset.albumLabels[label + 1]])
if (error):
    raise FileNotFoundError('Dataset is corrupted')

# SPLIT and LOAD DATA
trainLoader = DataLoader(augmentedDataset, batch_size=BATCH_SIZE, shuffle=True)
validationLoader = DataLoader(valDataset, batch_size=8, shuffle=True)

# CREATE MODEL
if (MODEL_NAME == ModelType.BABY_OUROBOROS):
    model = BabyOuroboros(numClasses=len(albumIndexes))
elif (MODEL_NAME == ModelType.OUROBOROS):
    model = Ouroboros(numClasses=len(albumIndexes), numLayers=UNFREEZE_LAYERS)
elif (MODEL_NAME == ModelType.AMPHISBAENA):
    model = Amphisbaena(numAlbums=len(albumIndexes), numArtists=len(artistIndexes), numLayers=UNFREEZE_LAYERS)
else:
    raise ValueError(f'Invalid model type: {MODEL_NAME}')
print(f'Created {MODEL_NAME.value} model')

if (MODEL_NAME == ModelType.AMPHISBAENA):
    # the Amphisbaena model requires two label sets
    artistClasses=vanillaDataset.artistLabels
    trainAmphi(
        model=model,
        trainLoader=trainLoader, validationLoader=validationLoader,
        maxEpochs=MAX_EPOCHS, learningRate=ALPHA, weightDecay=LAMBDA,
        patience=5, overallBestValLoss=float('inf'),
    )
else:
    # the Ouroboros models only require one label set
    artistClasses=None
    trainOuro(
        model=model,
        trainLoader=trainLoader, validationLoader=validationLoader,
        maxEpochs=MAX_EPOCHS, learningRate=ALPHA, weightDecay=LAMBDA,
        patience=5, overallBestValLoss=float('inf'),
    )

# LOAD MODEL FROM CHECKPOINT
checkpoint = torch.load(os.path.join(rootDir, 'bin', f'{MODEL_NAME.value}-checkpoint.pt'))
model.load_state_dict(checkpoint['modelStateDict'])
print(f'\nReloaded {MODEL_NAME.value} model from checkpoint (epoch {checkpoint["epoch"]})')

# EVALUATE MODEL
if (MODEL_NAME == ModelType.AMPHISBAENA):
    # the Amphisbaena model requires two label sets
    validateAmphi(model, valDataset, printResults=True)
    validateAmphi(model, testDataset, printResults=True)
else:
    # the Ouroboros models only require one label set
    validateOuro(model, valDataset, printResults=True)
    validateOuro(model, testDataset, printResults=True)

# SAVE THE MODEL
torch.save(
    {
        'modelStateDict': model.state_dict(),
        'albumClasses': vanillaDataset.albumLabels,
        'artistClasses': artistClasses,
        'metadata': {
            'modelType': MODEL_NAME.value,
            'alpha': ALPHA,
            'lambda': LAMBDA,
            'batchSize': BATCH_SIZE,
            'epochs': checkpoint['epoch'],
            'numAugmentations': NUM_AUGMENTATIONS,
            'unfreezeLayers': UNFREEZE_LAYERS,
            'trainset': trainDirs,
            'valset': valDirs,
            'testset': testDirs,
        }
    },
    os.path.join(rootDir, 'bin', f'{MODEL_NAME.value}.pth')
)

print(f'\nTraining completed in {time.time() - timer:.2f} seconds')
