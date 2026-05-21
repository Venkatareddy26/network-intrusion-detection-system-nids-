import warnings
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_sample_weight

warnings.filterwarnings("ignore")

from src.nids.data.loader import FEATURE_COLUMNS, get_label_mapping
from src.nids.utils.exceptions import (
    InferenceException,
    ModelLoadException,
    ModelNotLoadedException,
)
from src.nids.utils.logging import get_logger
from src.nids.utils.validators import validate_features

logger = get_logger(__name__)


class NIDSClassifier:
    """Network Intrusion Detection System classifier with XGBoost."""

    def __init__(self, label_mapping: Dict[str, int] = None):
        self.label_mapping = label_mapping or get_label_mapping()
        self.reverse_mapping = {v: k for k, v in self.label_mapping.items()}
        self.model = None
        self.feature_names = FEATURE_COLUMNS
        self.scale_pos_weight = 1.0

    def calculate_class_weights(self, y: np.ndarray) -> float:
        """Calculate scale_pos_weight for imbalanced classes."""
        classes, counts = np.unique(y, return_counts=True)
        if len(classes) < 2:
            return 1.0
        majority = max(counts)
        minority = min(counts)
        return majority / minority if minority > 0 else 1.0

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        use_smote: bool = True,
    ) -> Dict[str, Any]:
        """Train the XGBoost classifier with SMOTE for class imbalance.

        Args:
            X: Feature matrix
            y: Target labels
            test_size: Test set proportion
            use_smote: Whether to apply SMOTE

        Returns:
            Dictionary with training results

        Raises:
            InferenceException: If training fails
        """
        try:
            logger.info("Starting model training")
            validate_features(X)

            logger.info("Splitting data...")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            logger.info(f"Training set: {len(X_train)} samples")
            logger.info(f"Test set: {len(X_test)} samples")

            if use_smote:
                logger.info("Applying SMOTE for class imbalance...")
                try:
                    classes, counts = np.unique(y_train, return_counts=True)
                    min_count = int(counts.min())
                    target_per_minority_class = min(10000, int(counts.max()))
                    sampling_strategy = {
                        int(cls): target_per_minority_class
                        for cls, count in zip(classes, counts)
                        if count < target_per_minority_class and count >= 2
                    }
                    k_neighbors = max(1, min(5, min_count - 1))

                    if sampling_strategy:
                        smote = SMOTE(
                            random_state=42,
                            k_neighbors=k_neighbors,
                            sampling_strategy=sampling_strategy,
                        )
                    else:
                        smote = SMOTE(random_state=42, k_neighbors=k_neighbors)

                    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
                    logger.info(f"After SMOTE: {len(X_train_resampled)} samples")
                except Exception as e:
                    logger.warning(f"SMOTE failed: {e}. Continuing without SMOTE.")
                    X_train_resampled, y_train_resampled = X_train, y_train
            else:
                X_train_resampled, y_train_resampled = X_train, y_train

            self.scale_pos_weight = self.calculate_class_weights(y_train_resampled)

            logger.info("Training XGBoost model...")
            xgb_params = {
                "n_estimators": 200,
                "max_depth": 8,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42,
                "use_label_encoder": False,
                "eval_metric": "mlogloss",
                "n_jobs": -1,
            }
            if len(np.unique(y_train_resampled)) <= 2:
                xgb_params["scale_pos_weight"] = self.scale_pos_weight

            self.model = xgb.XGBClassifier(**xgb_params)
            sample_weight = compute_sample_weight(
                class_weight="balanced", y=y_train_resampled
            )

            self.model.fit(
                X_train_resampled,
                y_train_resampled,
                sample_weight=sample_weight,
                eval_set=[(X_test, y_test)],
                verbose=50,
            )

            y_pred = self.model.predict(X_test)
            f1_macro = f1_score(y_test, y_pred, average="macro")

            logger.info("\nClassification Report:")
            labels = sorted(self.reverse_mapping)
            target_names = [self.reverse_mapping[label] for label in labels]
            logger.info(
                classification_report(
                    y_test,
                    y_pred,
                    labels=labels,
                    target_names=target_names,
                    zero_division=0,
                )
            )

            logger.info(f"Macro F1 Score: {f1_macro:.4f}")

            return {"f1_macro": f1_macro, "y_test": y_test, "y_pred": y_pred}

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            raise InferenceException(f"Training failed: {str(e)}")

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict class labels and probabilities.

        Args:
            X: Feature matrix

        Returns:
            Tuple of (predictions, probabilities)

        Raises:
            ModelNotLoadedException: If model is not loaded
            InferenceException: If prediction fails
        """
        if self.model is None:
            raise ModelNotLoadedException("Model not trained or loaded")

        try:
            validate_features(X)
            y_pred = self.model.predict(X)
            y_proba = self.model.predict_proba(X)
            return y_pred, y_proba
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise InferenceException(f"Prediction failed: {str(e)}")

    def predict_single(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict for a single flow.

        Args:
            features: Feature array for single flow

        Returns:
            Dictionary with prediction results

        Raises:
            ModelNotLoadedException: If model is not loaded
            InferenceException: If prediction fails
        """
        if self.model is None:
            raise ModelNotLoadedException("Model not trained or loaded")

        try:
            features = np.asarray(features).reshape(1, -1)
            validate_features(features)

            y_pred = int(self.model.predict(features)[0])
            y_proba = self.model.predict_proba(features)[0]

            pred_label = self.reverse_mapping[y_pred]
            confidence = float(y_proba[y_pred])

            return {
                "prediction": pred_label,
                "confidence": confidence,
                "probabilities": {
                    self.reverse_mapping[i]: float(p) for i, p in enumerate(y_proba)
                },
            }
        except Exception as e:
            logger.error(f"Single prediction failed: {e}", exc_info=True)
            raise InferenceException(f"Single prediction failed: {str(e)}")

    def save(self, filepath: str):
        """Save model to disk.

        Args:
            filepath: Path to save model

        Raises:
            ModelLoadException: If save fails
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {
                    "model": self.model,
                    "label_mapping": self.label_mapping,
                    "scale_pos_weight": self.scale_pos_weight,
                    "feature_names": self.feature_names,
                },
                filepath,
            )
            logger.info(f"Model saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}", exc_info=True)
            raise ModelLoadException(f"Failed to save model: {str(e)}")

    def load(self, filepath: str):
        """Load model from disk.

        Args:
            filepath: Path to load model from

        Raises:
            ModelLoadException: If load fails
        """
        try:
            if not Path(filepath).exists():
                raise ModelLoadException(f"Model file not found: {filepath}")

            data = joblib.load(filepath)
            if isinstance(data, dict):
                self.model = data["model"]
                self.label_mapping = data.get("label_mapping", get_label_mapping())
                self.scale_pos_weight = data.get("scale_pos_weight", 1.0)
                self.feature_names = data.get("feature_names", FEATURE_COLUMNS)
            else:
                self.model = data
                self.label_mapping = get_label_mapping()
                self.scale_pos_weight = 1.0
                self.feature_names = FEATURE_COLUMNS
            self.reverse_mapping = {v: k for k, v in self.label_mapping.items()}
            logger.info(f"Model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise ModelLoadException(f"Failed to load model: {str(e)}")



def train_model(
    data_path: str, output_path: str = "models/nids_model.pkl"
) -> Tuple[NIDSClassifier, Dict[str, Any]]:
    """Train and save the NIDS model."""
    print(f"Loading data from {data_path}")
    df = pd.read_csv(data_path, low_memory=False)
    df.columns = df.columns.str.strip()

    from src.nids.data.loader import engineer_features, map_labels

    X = engineer_features(df)
    classifier = NIDSClassifier()
    if "Label" not in df.columns:
        raise InferenceException("Training data must include a Label column")

    y_raw = df["Label"].values
    y_mapped = np.array(
        [classifier.label_mapping.get(map_labels(str(label)), 0) for label in y_raw]
    )
    results = classifier.train(X.values, y_mapped)

    classifier.save(output_path)

    return classifier, results
