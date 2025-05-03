# Ouroboros Model Card

A simple CNN model used to classify images of vinyl records into specific album classes (`albumName_artistName_year`) from a fixed training dataset.

The model performs well on known data but cannot recognise unseen albums. It functions similarly to a reverse image search and is ineffective with out-of-distribution inputs. The name "Ouroboros" references the [ancient symbol of a snake eating its own tail](https://en.wikipedia.org/wiki/Ouroboros), reflecting the model's circular dependence on its own training data. "Baby" refers to the model's small size and early development stage.

## Model Details

- **Model Name:** BabyOuroboros (`modelling.models.BabyOuroboros`)
- **Model Type:** Single-headed convolutional neural network (CNN)
- **Developer:** [Jack Gillespie](https://github.com/Razzula/)
- **Version:** mini
- **Source Code:** [GitHub Repository](https://github.com/Razzula/virtual-turntable/tree/main/server/modelling/models)
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.en)

## Intended Use

- **Primary Use Case:** Image classification of vinyl album covers into known classes.
- **Users:** Researchers, music archivists, and developers working on media recognition.
- **Out-of-Scope Uses:** Cannot detect or classify albums not present in the training data.

## Factors

- **Data Sensitivity:** Model is sensitive to image resolution, lighting, and angle.
- **Bias:** Limited to training data; biased toward known album covers.
- **Instrumental Dependency:** Accuracy depends on preprocessing, camera quality, and input fidelity.

## Metrics

- **Evaluated Using:** Accuracy, precision, recall, F1-score.
- **Key Failure Modes:**
  - **False Positives:** Incorrectly identifying one known album as another.
  - **False Negatives:** Failing to recognise a correct known album.
  - **Out-of-Distribution Misclassification:** Always classifies unknown albums as one of the known classes.

## Evaluation Data

- **Dataset:** [Dataset Manifest](https://github.com/Razzula/virtual-turntable/blob/cb3e1561de8f4f9d98f850b8b971f118cdb5e25c/server/modelling/data/manifest.json)
- **Composition:** 12 classes (11 albums + null), 21 images total.
- **Breakdown:**
  - `Mini` Training Set: Early-stage subset with digitally sourced albums.
  - `Null` Class: A single image explicitly used for failure case calibration ([null.jpg](https://github.com/Razzula/virtual-turntable/blob/main/server/modelling/data/art_/_null/_null/null.jpg)).

## Training Data

- **Input:** Custom dataset of album cover images.
- **Preprocessing:** Images resized and normalised.
- **Limitations:** Small dataset with minimal class diversity; high overfitting risk.

## Quantitative Analyses

- **Method:** Accuracy and confusion matrix on hold-out set.
- **Findings:**
  - Performance degrades under poor lighting or camera conditions.
  - Model cannot distinguish unknown albums.
  - High variance in performance due to limited dataset.

## Ethical Considerations

- **Bias Awareness:** Reflects its narrow training distribution.
- **Misuse Risk:** Should not be used in production or critical applications.
- **Privacy:** No PII present in the training data.

## Caveats and Recommendations

- **Caveats:**
  - Cannot generalise beyond known data.
  - No support for unknown album detection.
- **Recommendations:**
  - Expand and diversify training dataset.
  - Add an out-of-distribution detector (e.g., null class calibration).
  - Consider scaling architecture and applying transfer learning for robustness.
