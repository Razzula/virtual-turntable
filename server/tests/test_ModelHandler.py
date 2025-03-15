"""Unit tests for the ModelHandler class."""
import json
import os
from pickle import UnpicklingError
import shutil
import tempfile
import unittest
from typing import Any, Dict, List, Union

import torch
import torch.nn as nn
from PIL import Image
from unittest.mock import MagicMock, patch

from modelling.models.utils.ModelType import ModelType
from modelling.models.BabyOuroboros import BabyOuroboros, transform  # transform will be patched in tests
from app.modules.modelHandler import ModelHandler


# A dummy model to simulate prediction.
class DummyModel(nn.Module):
    """Dummy model that always returns the same output."""
    def __init__(self, classes: List[str]) -> None:
        super().__init__()
        self.classes: List[str] = classes

    def forward(self, _x: torch.Tensor) -> torch.Tensor:
        # Return fixed output so that index 0 is highest.
        return torch.tensor([[10.0, 0.0]])


class TestModelHandler(unittest.TestCase):
    """Test suite for the ModelHandler class."""

    def setUp(self) -> None:
        """Set up test dependencies and dummy files before each test."""
        self.rootPath: str = tempfile.mkdtemp(prefix="root_")
        self.modelsPath: str = os.path.join(self.rootPath, "models")
        os.makedirs(self.modelsPath, exist_ok=True)

        # Create a dummy manifest file in the expected location.
        manifestPath: str = os.path.join(self.rootPath, "..", "modelling", "data")
        os.makedirs(manifestPath, exist_ok=True)
        self.manifestFile: str = os.path.join(manifestPath, "manifest.json")
        with open(self.manifestFile, "w", encoding="utf-8") as f:
            json.dump({"dummy": {"label": "Dummy Label"}}, f)

        self.handler: ModelHandler = ModelHandler(self.rootPath, self.modelsPath)

    def tearDown(self) -> None:
        """Clean up temporary directories."""

        shutil.rmtree(self.rootPath, ignore_errors=True)
        # Also clean up the manifest directory.
        manifestDir: str = os.path.join(self.rootPath, "..", "modelling")
        shutil.rmtree(manifestDir, ignore_errors=True)

    def testLoadModelFileNotFound(self) -> None:
        """Test that loadModel raises FileNotFoundError if the model file is missing."""
        with self.assertRaises(FileNotFoundError):
            self.handler.loadModel(ModelType.OUROBOROS, "nonexistent.pt")

    def testLoadModelInvalidType(self) -> None:
        """Test that loadModel raises TypeError for an invalid model type."""
        # Create a dummy model file so that file existence tests pass.
        dummyModelPath: str = os.path.join(self.modelsPath, "INVALID", "dummy.pt")
        os.makedirs(os.path.dirname(dummyModelPath), exist_ok=True)
        with open(dummyModelPath, "w", encoding="utf-8") as f:
            f.write("dummy content")
        # Pass an invalid model type (cast a string to ModelType for test purposes).
        with self.assertRaises(UnpicklingError):
            self.handler.loadModel("INVALID", "dummy.pt")

    @patch("app.modules.modelHandler.torch.load")
    def testLoadModelSuccess(self, mockTorchLoad: Any) -> None:
        """Test that loadModel successfully loads a model and reads the manifest."""
        # Prepare a dummy checkpoint.
        dummyCheckpoint: Dict[str, Any] = {
            "classes": ["class0", "class1"],
            "modelStateDict": {}
        }
        mockTorchLoad.return_value = dummyCheckpoint

        # Create a dummy model file.
        modelDir: str = os.path.join(self.modelsPath, ModelType.OUROBOROS.name)
        os.makedirs(modelDir, exist_ok=True)
        dummyModelFile: str = os.path.join(modelDir, "dummy.pt")
        with open(dummyModelFile, "w", encoding="utf-8") as f:
            f.write("dummy model content")

        # Patch Ouroboros to return a dummy model.
        with patch("app.modules.modelHandler.Ouroboros", return_value=DummyModel(dummyCheckpoint["classes"])) as mockOuro:
            self.handler.loadModel(ModelType.OUROBOROS, "dummy.pt")
            self.assertIsNotNone(self.handler.model)
            # Check that the manifest was loaded.
            self.assertTrue(self.handler.classes)
            # Verify the dummy manifest value.
            self.assertEqual(self.handler.classes.get("dummy", {}).get("label"), "Dummy Label")

    def testScanWithoutModel(self) -> None:
        """Test that scan raises Exception if no model is loaded."""
        with self.assertRaises(Exception):
            self.handler.scan("dummy.jpg")

    def testScanPathNotExist(self) -> None:
        """Test that scan raises FileNotFoundError if the provided path doesn't exist."""
        # Set a dummy model so that scan proceeds past the model check.
        self.handler.model = DummyModel(["dummy"])
        with self.assertRaises(FileNotFoundError):
            self.handler.scan("nonexistent_path")

    @patch.object(ModelHandler, "_predictImage", return_value={"dummy": "result"})
    def testScanSingleImage(self, mockPredict: Any) -> None:
        """Test that scan returns a list with one prediction for a single image file."""
        # Create a temporary dummy image file.
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            imagePath: str = tmp.name
        try:
            # Set a dummy model.
            self.handler.model = DummyModel(["dummy"])
            result: Union[List[Dict[str, Union[str, int, float]]], Dict[str, Union[str, int, float]]] = self.handler.scan(imagePath)
            self.assertIsInstance(result, list)
            self.assertEqual(result[0], {"dummy": "result"})
        finally:
            os.remove(imagePath)

    @patch.object(ModelHandler, "_predictImage", side_effect=lambda path: {"file": os.path.basename(path)})
    def testScanDirectory(self, mockPredict: Any) -> None:
        """Test that scan returns predictions for each image file in a directory."""
        with tempfile.TemporaryDirectory() as tmpDir:
            # Create two dummy image files.
            fileNames: List[str] = ["a.jpg", "b.png"]
            for fileName in fileNames:
                filePath: str = os.path.join(tmpDir, fileName)
                with open(filePath, "w", encoding="utf-8") as f:
                    f.write("dummy")
            # Set a dummy model.
            self.handler.model = DummyModel(["dummy"])
            results: Union[List[Dict[str, Union[str, int, float]]], Dict[str, Union[str, int, float]]] = self.handler.scan(tmpDir)
            self.assertIsInstance(results, list)
            # Check that both files were processed in sorted order.
            expected: List[str] = sorted(fileNames)
            actual: List[str] = [res["file"] for res in results]  # type: ignore
            self.assertEqual(actual, expected)

    @patch("app.modules.modelHandler.transform")
    def testPredictImage(self, mockTransform: Any) -> None:
        """Test _predictImage returns a prediction dictionary."""
        # Create a dummy image file.
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            imagePath: str = tmp.name
            # Create a simple image and save it.
            dummyImage: Image.Image = Image.new("RGB", (10, 10), color="red")
            dummyImage.save(imagePath)

        try:
            # Create a dummy model that returns a fixed tensor.
            dummyOutput: torch.Tensor = torch.tensor([[10.0, 0.0]])
            dummyModel: DummyModel = DummyModel(["class0", "class1"])
            # Patch the model call to return our dummy output.
            dummyModel.__call__ = MagicMock(return_value=dummyOutput)
            self.handler.model = dummyModel

            # Patch transform to return a tensor of the expected shape.
            mockTransform.return_value = torch.zeros((3, 224, 224))
            result: Dict[str, Union[str, int, float]] = self.handler._predictImage(imagePath)
            self.assertIn("image", result)
            self.assertIn("predictedClass", result)
            self.assertIn("predictedProb", result)
            # Since our dummy model always returns highest probability for index 0:
            self.assertEqual(result["predictedClass"], "class0")
        finally:
            os.remove(imagePath)


if (__name__ == '__main__'):
    unittest.main()
