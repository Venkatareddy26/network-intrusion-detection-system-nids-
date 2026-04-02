import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, confusion_matrix
from imblearn.over_sampling import SMOTE
import joblib
import os
from typing import Tuple, Dict, Any
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from src.nids.data.loader import FEATURE_COLUMNS, get_label_mapping
from src.nids.utils.exceptions import (
    ModelLoadException,
    ModelNotLoadedException,
    InferenceException,
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
                    smote = SMOTE(random_state=42, k_neighbors=5)
                    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
                    logger.info(f"After SMOTE: {len(X_train_resampled)} samples")
                except Exception as e:
                    logger.warning(f"SMOTE failed: {e}. Continuing without SMOTE.")
                    X_train_resampled, y_train_resampled = X_train, y_train
            else:
                X_train_resampled, y_train_resampled = X_train, y_train

            self.scale_pos_weight = self.calculate_class_weights(y_train_resampled)

            logger.info("Training XGBoost model...")
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=self.scale_pos_weight,
                random_state=42,
                use_label_encoder=False,
                eval_metric="mlogloss",
                n_jobs=-1,
            )

            self.model.fit(
                X_train_resampled,
                y_train_resampled,
                eval_set=[(X_test, y_test)],
                verbose=50,
            )

            y_pred = self.model.predict(X_test)
            f1_macro = f1_score(y_test, y_pred, average="macro")

            logger.info("\nClassification Report:")
            logger.info(
                classification_report(
                    y_test, y_pred, target_names=list(self.label_mapping.keys())
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
            features = features.reshape(1, -1)
            validate_features(features)

            y_pred = self.model.predict(features)[0]
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
            self.model = data["model"]
            self.label_mapping = data["label_mapping"]
            self.scale_pos_weight = data.get("scale_pos_weight", 1.0)
            self.feature_names = data.get("feature_names", FEATURE_COLUMNS)
            self.reverse_mapping = {v: k for k, v in self.label_mapping.items()}
            logger.info(f"Model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise ModelLoadException(f"Failed to load model: {str(e)}")


def train_model(
    data_path: str, output_path: str = "models/nids_model.pkl"
) -> NIDSClassifier:
    """Train and save the NIDS model."""
    print(f"Loading data from {data_path}")
    df = pd.read_csv(data_path, low_memory=False)

    from src.nids.data.loader import engineer_features, map_labels

    X = engineer_features(df)
    y_raw = df["Label"].values if "Label" in df.columns else df["Label"].values
    y_mapped = np.array([self.label_mapping.get(map_labels(l), 0) for l in y_raw])

    classifier = NIDSClassifier()
    results = classifier.train(X.values, y_mapped)

    classifier.save(output_path)

    return classifier, results
