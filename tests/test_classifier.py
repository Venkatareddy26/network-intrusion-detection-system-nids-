"""Classifier tests."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.nids.models.classifier import NIDSClassifier
from src.nids.data.loader import get_label_mapping
from src.nids.utils.exceptions import ModelNotLoadedException, InferenceException


@pytest.fixture
def classifier():
    """Create classifier instance."""
    return NIDSClassifier()


@pytest.fixture
def sample_data():
    """Create sample training data."""
    np.random.seed(42)
    n_samples = 1000
    n_features = 30

    X = np.random.randn(n_samples, n_features)
    y = np.random.randint(0, 5, n_samples)

    return X, y


def test_classifier_initialization(classifier):
    """Test classifier initialization."""
    assert classifier.model is None
    assert classifier.label_mapping is not None
    assert len(classifier.label_mapping) == 5


def test_classifier_train(classifier, sample_data):
    """Test classifier training."""
    X, y = sample_data
    results = classifier.train(X, y, test_size=0.2, use_smote=False)

    assert "f1_macro" in results
    assert classifier.model is not None
    assert 0.0 <= results["f1_macro"] <= 1.0


def test_classifier_predict_without_training(classifier, sample_data):
    """Test prediction without training."""
    X, _ = sample_data

    with pytest.raises(ModelNotLoadedException):
        classifier.predict(X[:10])


def test_classifier_predict_single(classifier, sample_data):
    """Test single prediction."""
    X, y = sample_data
    classifier.train(X, y, test_size=0.2, use_smote=False)

    features = X[0:1]
    result = classifier.predict_single(features)

    assert "prediction" in result
    assert "confidence" in result
    assert "probabilities" in result
    assert 0.0 <= result["confidence"] <= 1.0


def test_classifier_save_load(classifier, sample_data):
    """Test model save and load."""
    X, y = sample_data
    classifier.train(X, y, test_size=0.2, use_smote=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "test_model.pkl"
        classifier.save(str(model_path))

        assert model_path.exists()

        new_classifier = NIDSClassifier()
        new_classifier.load(str(model_path))

        assert new_classifier.model is not None
        assert new_classifier.label_mapping == classifier.label_mapping


def test_classifier_invalid_features(classifier, sample_data):
    """Test prediction with invalid features."""
    X, y = sample_data
    classifier.train(X, y, test_size=0.2, use_smote=False)

    # Wrong number of features
    invalid_features = np.random.randn(1, 10)

    with pytest.raises(InferenceException):
        classifier.predict_single(invalid_features)


def test_classifier_nan_features(classifier, sample_data):
    """Test prediction with NaN features."""
    X, y = sample_data
    classifier.train(X, y, test_size=0.2, use_smote=False)

    features = X[0:1].copy()
    features[0, 0] = np.nan

    with pytest.raises(InferenceException):
        classifier.predict_single(features)
