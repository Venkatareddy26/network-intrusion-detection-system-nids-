"""
NIDS Model Training Pipeline
-----------------------------
Trains XGBoost classifier with SMOTE on synthetic (or real) data.
Supports both synthetic generation and CICIDS2017 CSV loading.

Usage:
    python train_model.py                    # Train on generated synthetic data
    python train_model.py --data data/CICIDS2017.csv  # Train on real CICIDS2017
"""

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nids.data.generate_synthetic import generate_dataset
from src.nids.data.loader import FEATURE_COLUMNS, engineer_features, get_label_mapping, map_labels
from src.nids.models.classifier import NIDSClassifier


def train_on_dataframe(df: pd.DataFrame, output_path: str = "models/nids_model.pkl"):
    """Train the NIDS model on a DataFrame with Label column."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    print("\n" + "=" * 60)
    print("  NIDS MODEL TRAINING PIPELINE")
    print("=" * 60)

    label_mapping = get_label_mapping()
    print(f"\nLabel mapping: {label_mapping}")

    # Feature engineering
    print("\n[1/4] Feature engineering...")
    X = engineer_features(df)
    print(f"  Feature matrix shape: {X.shape}")

    # Map labels
    print("\n[2/4] Mapping labels...")
    if "Label" not in df.columns:
        raise ValueError("Training data must include a Label column")
    y_raw = df["Label"].values
    y = np.array([label_mapping.get(map_labels(str(label_val)), 0) for label_val in y_raw])

    unique, counts = np.unique(y, return_counts=True)
    reverse_mapping = {v: k for k, v in label_mapping.items()}
    print("  Class distribution:")
    for cls_id, count in zip(unique, counts):
        pct = count / len(y) * 100
        print(f"    {reverse_mapping.get(cls_id, f'class_{cls_id}'):20s}: {count:>6,} ({pct:.1f}%)")

    # Train
    print("\n[3/4] Training XGBoost with SMOTE...")
    classifier = NIDSClassifier(label_mapping)
    start_time = time.time()
    results = classifier.train(X.values.astype(np.float32), y, test_size=0.2, use_smote=True)
    train_time = time.time() - start_time

    # Save
    print(f"\n[4/4] Saving model to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    classifier.save(output_path)

    # Summary
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"  ✅ Macro F1 Score : {results['f1_macro']:.4f}")
    print(f"  ✅ Training Time  : {train_time:.1f}s")
    print(f"  ✅ Model Saved    : {output_path}")
    print(f"  ✅ Features       : {len(FEATURE_COLUMNS)}")
    print(f"  ✅ Classes        : {list(label_mapping.keys())}")

    target_f1 = 0.97
    if results['f1_macro'] >= target_f1:
        print(f"\n  🎯 TARGET MET: F1 {results['f1_macro']:.4f} >= {target_f1}")
    else:
        print(f"\n  ⚠️  TARGET MISSED: F1 {results['f1_macro']:.4f} < {target_f1}")
        print("     Consider training on real CICIDS2017 data for better results.")

    print("=" * 60)
    return classifier, results


def train_synthetic(output_path: str = "models/nids_model.pkl"):
    """Train on synthetically generated data."""
    print("\n📊 Generating synthetic training data...")
    df = generate_dataset(
        n_normal=50000,
        n_dos=2000,
        n_portscan=1500,
        n_bruteforce=1000,
        n_exfil=500,
        seed=42,
    )
    # Save synthetic data for reference
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/nids_synthetic.csv", index=False)
    print("  Synthetic data saved to data/nids_synthetic.csv")

    return train_on_dataframe(df, output_path)


def train_cicids(data_path: str, output_path: str = "models/nids_model.pkl"):
    """Train on real CICIDS2017 CSV data."""
    print(f"\n📊 Loading CICIDS2017 from {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    print(f"  Loaded {len(df):,} rows")

    return train_on_dataframe(df, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train NIDS XGBoost model")
    parser.add_argument(
        "--data", type=str, default=None,
        help="Path to CICIDS2017 CSV file. If omitted, uses synthetic data."
    )
    parser.add_argument(
        "--output", type=str, default="models/nids_model.pkl",
        help="Output path for trained model (default: models/nids_model.pkl)"
    )
    args = parser.parse_args()

    if args.data:
        train_cicids(args.data, args.output)
    else:
        train_synthetic(args.output)
