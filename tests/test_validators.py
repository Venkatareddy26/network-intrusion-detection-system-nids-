"""Validator tests."""

import pytest
import numpy as np
import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create required directories
Path("logs").mkdir(exist_ok=True)

from src.nids.utils.validators import (
    validate_features,
    validate_ip_address,
    sanitize_input,
    validate_confidence_threshold,
)
from src.nids.utils.exceptions import InvalidFeatureException


def test_validate_features_valid():
    """Test feature validation with valid data."""
    features = np.random.randn(1, 30)
    validate_features(features)  # Should not raise


def test_validate_features_wrong_shape():
    """Test feature validation with wrong shape."""
    features = np.random.randn(1, 10)

    with pytest.raises(InvalidFeatureException):
        validate_features(features)


def test_validate_features_nan():
    """Test feature validation with NaN values."""
    features = np.random.randn(1, 30)
    features[0, 0] = np.nan

    with pytest.raises(InvalidFeatureException):
        validate_features(features)


def test_validate_features_inf():
    """Test feature validation with Inf values."""
    features = np.random.randn(1, 30)
    features[0, 0] = np.inf

    with pytest.raises(InvalidFeatureException):
        validate_features(features)


def test_validate_features_negative():
    """Test feature validation with negative values."""
    features = np.random.randn(1, 30)
    features[0, 0] = -1000.0  # flow_duration should be positive

    with pytest.raises(InvalidFeatureException):
        validate_features(features)


def test_validate_ip_address_valid():
    """Test IP address validation with valid IPs."""
    assert validate_ip_address("192.168.1.1") is True
    assert validate_ip_address("10.0.0.1") is True
    assert validate_ip_address("0.0.0.0") is True
    assert validate_ip_address("255.255.255.255") is True


def test_validate_ip_address_invalid():
    """Test IP address validation with invalid IPs."""
    assert validate_ip_address("999.999.999.999") is False
    assert validate_ip_address("192.168.1") is False
    assert validate_ip_address("not.an.ip.address") is False
    assert validate_ip_address("192.168.1.1.1") is False


def test_sanitize_input():
    """Test input sanitization."""
    data = {
        "name": "<script>alert('xss')</script>",
        "value": "normal&value",
        "number": 123,
    }

    sanitized = sanitize_input(data)

    assert "<" not in sanitized["name"]
    assert ">" not in sanitized["name"]
    assert "&" not in sanitized["value"]
    assert sanitized["number"] == 123


def test_validate_confidence_threshold_valid():
    """Test confidence threshold validation with valid values."""
    validate_confidence_threshold(0.5)  # Should not raise
    validate_confidence_threshold(0.0)
    validate_confidence_threshold(1.0)


def test_validate_confidence_threshold_invalid():
    """Test confidence threshold validation with invalid values."""
    with pytest.raises(InvalidFeatureException):
        validate_confidence_threshold(-0.1)

    with pytest.raises(InvalidFeatureException):
        validate_confidence_threshold(1.1)

    with pytest.raises(InvalidFeatureException):
        validate_confidence_threshold("not a number")
