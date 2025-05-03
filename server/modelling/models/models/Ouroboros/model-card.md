# Ouroboros Model Card

A ResNet-based model for classifying vinyl record album images into known album classes (`albumName_artistName_year`) using transfer learning.

Unlike its predecessor (BabyOuroboros), this version leverages a pretrained ResNet-18 architecture for improved feature extraction and robustness across a larger and more diverse dataset. The model retains high accuracy for known inputs, but remains ineffective on unseen or out-of-distribution samples.

## Model Details

- **Model Name:** Ouroboros (`modelling.models.Ouroboros`)
- **Model Type:** Transfer learning (ResNet-18 backbone)
- **Developer:** [Jack Gillespie](https://github.com/Razzula/)
- **Version:** large
- **Source Code:** [GitHub Repository](https://github.com/Razzula/virtual-turntable/tree/main/server/modelling/models)
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.en)

## Intended Use

- **Primary Use Case:** Image classification of vinyl album covers into a known class set.
- **Users:** Researchers, archivists, and developers building media classifiers.
- **Out-of-Scope Uses:** Cannot detect or reject inputs outside the training set.

## Factors

- **Data Sensitivity:** Sensitive to resolution and lighting; robustness improved via augmentation.
- **Bias:** Reflects the structure and distribution of its training data; biased toward known artworks.
- **Instrumental Dependency:** Performance depends on preprocessing, camera fidelity, and consistent image sizing.

## Metrics

- **Evaluated Using:** Accuracy, F1-score, confusion matrix.
- **Key Failure Modes:**
  - **False Positives/Negatives:** Misclassifications among known classes.
  - **Out-of-Distribution Misclassification:** Unknown inputs always mapped to known classes.

## Evaluation Data

- **Dataset:** [Album Dataset Manifest](https://github.com/Razzula/virtual-turntable/blob/63f087f36f2dacd62cf51ccb8731cc891d10850c/server/modelling/data/albums.json)
- **Composition:** 103 classes, 196 original images.
- **Breakdown:**
  - Includes all data from the `Mini` set.
  - +58 digitally-sourced albums (113 images)
  - +20 physically-sourced albums (39 images)
  - +13 dual-format albums (23 images)
- **Augmented Variant:**
  - Augmentation used during training: jitter, rotation, blur, noise.
  - Effective sample size increased to 1,176 images.

## Training Data

- **Source:** Curated dataset of vinyl album artwork.
- **Preprocessing:** Images resized (244×244), normalised, and augmented per-epoch.
- **Limitations:** Closed-world setup; does not support unknown classes.

## Quantitative Analyses

- **Approach:** Hyperparameter grid search, layer unfreezing, and image resolution tuning.
- **Findings:**
  - Best performance with 2 ResNet layers unfrozen.
  - Augmentation significantly improved robustness.
  - 244×244 input resolution was optimal for performance vs. training time.

## Ethical Considerations

- **Bias Awareness:** Limited to known albums; risks bias in broader domains.
- **Misuse Risk:** Not suited for real-world general album detection or catalogue indexing.
- **Privacy:** No PII involved in data collection or training.

## Caveats and Recommendations

- **Caveats:**
  - Cannot handle albums not present in training set.
  - Poor rejection mechanism for novel inputs.
- **Recommendations:**
  - Improve OOD (out-of-distribution) rejection mechanism (e.g., null class).
  - Investigate deeper backbones or ensemble methods.
  - Explore fine-tuning with additional diverse and real-world data.
