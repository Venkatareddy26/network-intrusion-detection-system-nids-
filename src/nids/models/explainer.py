from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import shap


class SHAPExplainer:
    """SHAP-based explainer for NIDS alerts."""

    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        self._init_explainer()

    def _init_explainer(self):
        """Initialize SHAP TreeExplainer."""
        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            print(f"Warning: Could not initialize SHAP explainer: {e}")
            self.explainer = None

    def explain_prediction(
        self, features: np.ndarray, top_k: int = 3, class_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate SHAP explanation for a single prediction."""
        feature_matrix = self._as_feature_matrix(features)
        class_index = self._resolve_class_index(feature_matrix, class_index)

        if self.explainer is None:
            return self._fallback_explain(feature_matrix, top_k)

        try:
            shap_values = self.explainer.shap_values(feature_matrix)
            shap_vals = self._select_class_shap_values(shap_values, class_index)

            if shap_vals.shape[0] != len(self.feature_names):
                raise ValueError(
                    f"Expected {len(self.feature_names)} SHAP values, got {shap_vals.shape[0]}"
                )

            abs_shap = np.abs(shap_vals)
            top_indices = np.argsort(abs_shap)[-top_k:][::-1]

            top_features = []
            for idx in top_indices:
                top_features.append(
                    {
                        "feature": self.feature_names[idx],
                        "value": float(feature_matrix[0][idx]),
                        "importance": float(shap_vals[idx]),
                        "abs_importance": float(abs_shap[idx]),
                    }
                )

            return {
                "top_features": top_features,
                "base_value": self._select_expected_value(class_index),
            }

        except Exception as e:
            print(f"Error computing SHAP values: {e}")
            return self._fallback_explain(feature_matrix, top_k)

    def _as_feature_matrix(self, features: np.ndarray) -> np.ndarray:
        """Return features as a single-row matrix."""
        feature_matrix = np.asarray(features, dtype=float)
        if feature_matrix.ndim == 1:
            feature_matrix = feature_matrix.reshape(1, -1)
        elif feature_matrix.ndim > 2:
            feature_matrix = feature_matrix.reshape(1, -1)
        return feature_matrix

    def _resolve_class_index(
        self, feature_matrix: np.ndarray, class_index: Optional[int]
    ) -> int:
        """Resolve the class to explain, defaulting to the model prediction."""
        if class_index is not None:
            return int(class_index)

        if hasattr(self.model, "predict"):
            try:
                return int(self.model.predict(feature_matrix)[0])
            except Exception:
                return 0

        return 0

    def _select_class_shap_values(self, shap_values: Any, class_index: int) -> np.ndarray:
        """Normalize SHAP outputs across SHAP/XGBoost versions."""
        if isinstance(shap_values, list):
            selected = shap_values[min(class_index, len(shap_values) - 1)]
            return np.asarray(selected)[0]

        shap_array = np.asarray(shap_values)
        if shap_array.ndim == 2:
            return shap_array[0]

        if shap_array.ndim == 3:
            if shap_array.shape[1] == len(self.feature_names):
                selected_class = min(class_index, shap_array.shape[2] - 1)
                return shap_array[0, :, selected_class]
            if shap_array.shape[2] == len(self.feature_names):
                selected_class = min(class_index, shap_array.shape[0] - 1)
                return shap_array[selected_class, 0, :]

        raise ValueError(f"Unsupported SHAP output shape: {shap_array.shape}")

    def _select_expected_value(self, class_index: int) -> float:
        """Return the expected value for the explained class when available."""
        expected_value = getattr(self.explainer, "expected_value", 0.0)
        expected_array = np.asarray(expected_value)

        if expected_array.ndim == 0:
            return float(expected_array)

        selected_class = min(class_index, expected_array.shape[0] - 1)
        return float(expected_array[selected_class])

    def _fallback_explain(self, features: np.ndarray, top_k: int = 3) -> Dict[str, Any]:
        """Fallback explanation using feature importance."""
        feature_matrix = self._as_feature_matrix(features)
        if not hasattr(self.model, "feature_importances_"):
            return {
                "top_features": [],
                "base_value": 0.0,
                "error": "Model does not support feature importance",
            }

        importances = self.model.feature_importances_
        if len(importances) != len(self.feature_names):
            return {
                "top_features": [],
                "base_value": 0.0,
                "error": "Feature importance length does not match feature names",
            }

        top_indices = np.argsort(importances)[-top_k:][::-1]

        top_features = []
        for idx in top_indices:
            top_features.append(
                {
                    "feature": self.feature_names[idx],
                    "value": float(feature_matrix[0][idx]),
                    "importance": float(importances[idx]),
                    "abs_importance": float(importances[idx]),
                }
            )

        return {"top_features": top_features, "base_value": 0.0, "fallback": True}

    def explain_batch(
        self, features: np.ndarray, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate SHAP explanations for a batch of predictions."""
        explanations = []
        for i in range(len(features)):
            exp = self.explain_prediction(features[i], top_k)
            explanations.append(exp)
        return explanations


def create_explainer(model_path: str, feature_names: List[str]) -> SHAPExplainer:
    """Create a SHAP explainer from a saved model."""
    data = joblib.load(model_path)
    if isinstance(data, dict):
        model = data["model"]
    else:
        model = data
    return SHAPExplainer(model, feature_names)
