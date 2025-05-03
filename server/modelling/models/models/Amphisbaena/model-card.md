# Amphisbaena Model Card

A two-headed ResNet-based model for classifying vinyl record album images into both album and artist classes. This model extends the Ouroboros architecture to predict multiple labels per image, enabling shared feature learning across tasks.

Amphisbaena is named after the mythological two-headed serpent, reflecting the dual-headed nature of the architecture. This setup enables a single model to make both album and artist predictions, reducing duplication of effort and computational cost compared to separate models.

## Model Details

- **Model Name:** Amphisbaena (`modelling.models.Amphisbaena`)
- **Model Type:** Multi-headed ResNet-18 (transfer learning)
- **Developer:** [Jack Gillespie](https://github.com/Razzula/)
- **Version:** alpha
- **Source Code:** [GitHub Repository](https://github.com/Razzula/virtual-turntable/tree/main/server/modelling/models)
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.en)

## Intended Use

- **Primary Use Case:** Joint classification of album and artist from vinyl album covers.
- **Users:** Researchers in media recognition, multitask learning, and stylistic inference.
- **Out-of-Scope Uses:** Not designed for unknown or out-of-distribution class rejection.

## Factors

- **Data Sensitivity:** Performance may vary with visual consistency of album art; artist prediction is less reliable when album designs vary significantly.
- **Bias:** Inherits training data distribution bias; consistent styles (e.g., Ed Sheeran) perform better.
- **Instrumental Dependency:** Accuracy depends on consistent preprocessing, lighting, and image fidelity.

## Metrics

- **Evaluated Using:** Weighted F1-score (averaged across both heads), confusion matrices.
- **Key Failure Modes:**
  - **False Positives:** Misidentifying albums with similar style or typography.
  - **False Artists:** Artist prediction can be unreliable when no stylistic cues are shared.
  - **Out-of-Distribution Misclassification:** No support for novel artist or album detection.

## Evaluation Data

- **Dataset:** [Album Dataset Manifest](https://github.com/Razzula/virtual-turntable/blob/63f087f36f2dacd62cf51ccb8731cc891d10850c/server/modelling/data/albums.json)
- **Composition:** Subset of 103 classes used for album and artist identification.
- **Examples:** Includes visually consistent artist sets, such as Ed Sheeran's albums.

## Training Data

- **Source:** Curated album artworks with both album and artist labels.
- **Preprocessing:** Images resized (244×244), normalised, and augmented.
- **Limitations:** Artist prediction is less consistent across visually diverse albums.

## Quantitative Analyses

- **Method:** Dual loss training (CrossEntropy per head), with validation and early stopping.
- **Findings:**
  - Artist predictions are most effective when album designs share stylistic elements.
  - Album prediction remains robust under dual-head setup.
  - Model performance varies with artist consistency; ideal cases (e.g., Ed Sheeran) achieve >60% artist confidence on unseen variants.

## Ethical Considerations

- **Bias Awareness:** Model encodes visual style bias; success may depend on design patterns rather than true authorship.
- **Misuse Risk:** Not reliable for accurate artist attribution in legal or commercial contexts.
- **Privacy:** No personal data or identifiable features in the dataset.

## Caveats and Recommendations

- **Caveats:**
  - While Amphisbaena Alpha performed well in controlled or ideal conditions—particularly where visual consistency existed between an artist's albums—it was not thoroughly tested under more realistic or pessimistic scenarios. As such, this version remains an experimental proof-of-concept and is marked as *alpha* accordingly.
  - Artist prediction may fail on visually dissimilar works.
  - No handling of previously unseen artists.
  - Poor handling of unseen albums in isolation (output can inform an oCR system, for example, though).

- **Recommendations:**
  - Improve artist classification through larger, stylistically diverse datasets.
  - Explore use of auxiliary metadata (e.g., genre, decade) to support multitask learning.
  - Consider ensemble or attention-based extensions to better decouple style from identity.
