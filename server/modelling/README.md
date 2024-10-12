# Modelling

This directory contains the tools and scripts used to retrieve, handle, and process data used to create the CNN models used in the project for the identification of vinyl records.

## Usage

`./models/train.py` is the main script used to train the models.

Models can be found in `./models/models/`.

(Please refer to the individual `.ipynb` files for the experiments.)

### [Ouroboros](https://en.wikipedia.org/wiki/Ouroboros)

A simple CNN model that is used to classify an image of vinyl records as one of the classes (albums) used in the training dataset. The classes are 'ID's of the albums (`albumName_artistName_year`).

This model can, in theory, perform quite well on images of albums that are in the dataset (not just exclusively the same images themselves). However, it has no robustness against out-of-distribution albums; it will never predict an unknown album, as there is no generative aspect. This model _essentially_ performs as a reverse image search engine. Therefore, it is only functional when it is fed data that is similar to the training data.

Hence, the model is named Ouroboros, after the ancient symbol of a snake eating its own tail.
