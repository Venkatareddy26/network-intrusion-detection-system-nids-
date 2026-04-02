"""NIDS - Network Intrusion Detection System"""

from src.nids.data.loader import (
    FEATURE_COLUMNS,
    ATTACK_LABELS,
    ATTACK_CATEGORIES,
    load_cicids2017,
    engineer_features,
    map_labels,
    get_label_mapping,
)

from src.nids.models.classifier import NIDSClassifier
from src.nids.models.explainer import SHAPExplainer
from src.nids.pipeline.processor import (
    NetworkFlow,
    Alert,
    AlertQueue,
    Pipeline,
    simulate_flow,
)

__version__ = "1.0.0"

__all__ = [
    "FEATURE_COLUMNS",
    "ATTACK_LABELS",
    "ATTACK_CATEGORIES",
    "load_cicids2017",
    "engineer_features",
    "map_labels",
    "get_label_mapping",
    "NIDSClassifier",
    "SHAPExplainer",
    "NetworkFlow",
    "Alert",
    "AlertQueue",
    "Pipeline",
    "simulate_flow",
]
