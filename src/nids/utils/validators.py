"""Input validation utilities."""

from typing import Any, Dict

import numpy as np

from src.nids.data.loader import FEATURE_COLUMNS
from src.nids.utils.exceptions import InvalidFeatureException


def validate_features(features: np.ndarray) -> None:
    """Validate feature array.

    Args:
        features: Feature array to validate

    Raises:
        InvalidFeatureException: If features are invalid
    """
    if features is None:
        raise InvalidFeatureException("Features cannot be None")

    if not isinstance(features, np.ndarray):
        raise InvalidFeatureException("Features must be a numpy array")

    if features.ndim == 1:
        features = features.reshape(1, -1)

    if features.shape[1] != len(FEATURE_COLUMNS):
        raise InvalidFeatureException(
            f"Expected {len(FEATURE_COLUMNS)} features, got {features.shape[1]}"
        )

    # Check for NaN or Inf
    if np.isnan(features).any():
        raise InvalidFeatureException("Features contain NaN values")

    if np.isinf(features).any():
        raise InvalidFeatureException("Features contain Inf values")

    # Check for negative values where they shouldn't exist
    negative_check_indices = [0, 1, 2, 3, 4, 9, 10]  # Duration, packets, bytes, rates
    for idx in negative_check_indices:
        if (features[:, idx] < 0).any():
            raise InvalidFeatureException(
                f"Feature {FEATURE_COLUMNS[idx]} contains negative values"
            )


def validate_ip_address(ip: str) -> bool:
    """Validate IP address format.

    Args:
        ip: IP address string

    Returns:
        True if valid, False otherwise
    """
    import re

    ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(ipv4_pattern, ip):
        return False

    parts = ip.split(".")
    return all(0 <= int(part) <= 255 for part in parts)


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize input data to prevent injection attacks.

    Args:
        data: Input dictionary

    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Remove potentially dangerous characters
            value = value.replace("<", "").replace(">", "").replace("&", "")
            value = value[:1000]  # Limit string length
        sanitized[key] = value
    return sanitized


def validate_confidence_threshold(threshold: float) -> None:
    """Validate confidence threshold.

    Args:
        threshold: Confidence threshold value

    Raises:
        InvalidFeatureException: If threshold is invalid
    """
    if not isinstance(threshold, (int, float)):
        raise InvalidFeatureException("Threshold must be a number")

    if not 0.0 <= threshold <= 1.0:
        raise InvalidFeatureException("Threshold must be between 0.0 and 1.0")
