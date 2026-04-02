import numpy as np
import shap
from typing import Dict, List, Any, Tuple
import joblib


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
        self, features: np.ndarray, top_k: int = 3
    ) -> Dict[str, Any]:
        """Generate SHAP explanation for a single prediction."""
        if self.explainer is None:
            return self._fallback_explain(features, top_k)

        try:
            features = features.reshape(1, -1)
            shap_values = self.explainer.shap_values(features)

            if isinstance(shap_values, list):
                shap_vals = shap_values[0][0]
            else:
                shap_vals = shap_values[0]

            abs_shap = np.abs(shap_vals)
            top_indices = np.argsort(abs_shap)[-top_k:][::-1]

            top_features = []
            for idx in top_indices:
                top_features.append(
                    {
                        "feature": self.feature_names[idx],
                        "value": float(features[0][idx]),
                        "importance": float(shap_vals[idx]),
                        "abs_importance": float(abs_shap[idx]),
                    }
                )

            return {
                "top_features": top_features,
                "base_value": float(self.explainer.expected_value[0])
                if isinstance(self.explainer.expected_value, (list, np.ndarray))
                else float(self.explainer.expected_value),
            }

        except Exception as e:
            print(f"Error computing SHAP values: {e}")
            return self._fallback_explain(features, top_k)

    def _fallback_explain(self, features: np.ndarray, top_k: int = 3) -> Dict[str, Any]:
        """Fallback explanation using feature importance."""
        if not hasattr(self.model, "feature_importances_"):
            return {
                "top_features": [],
                "base_value": 0.0,
                "error": "Model does not support feature importance",
            }

        importances = self.model.feature_importances_
        top_indices = np.argsort(importances)[-top_k:][::-1]

        top_features = []
        for idx in top_indices:
            top_features.append(
                {
                    "feature": self.feature_names[idx],
                    "value": float(features[0][idx]),
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
    model = data["model"]
    return SHAPExplainer(model, feature_names)
