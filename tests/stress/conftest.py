"""Pytest configuration and fixtures for stress tests."""

import numpy as np
import pandas as pd
import pytest

from src.nids.data.loader import FEATURE_COLUMNS, get_label_mapping


@pytest.fixture
def sample_features():
    """Generate sample feature data for testing."""
    np.random.seed(42)
    n_samples = 1000
    n_features = len(FEATURE_COLUMNS)

    # Generate random features
    X = np.random.rand(n_samples, n_features) * 100
    return X


@pytest.fixture
def sample_labels():
    """Generate sample labels for testing."""
    np.random.seed(42)
    n_samples = 1000

    # Generate labels: 80% normal (0), 20% attacks (1-4)
    labels = np.random.choice([0, 0, 0, 0, 1, 2, 3, 4], size=n_samples)
    return labels


@pytest.fixture
def sample_dataframe():
    """Generate sample DataFrame for testing."""
    np.random.seed(42)
    n_samples = 1000

    data = {col: np.random.rand(n_samples) * 100 for col in FEATURE_COLUMNS}
    data['Label'] = np.random.choice(['Normal', 'DoS', 'Port Scan'], size=n_samples)

    return pd.DataFrame(data)


@pytest.fixture
def temp_csv_file(tmp_path, sample_dataframe):
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    sample_dataframe.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def label_mapping():
    """Get label mapping."""
    return get_label_mapping()
