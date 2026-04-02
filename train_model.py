import sys
import os
import pandas as pd
import numpy as np
from src.nids.models.classifier import NIDSClassifier
from src.nids.data.loader import engineer_features, map_labels, get_label_mapping


def train_with_synthetic_data(output_path: str = "models/nids_model.pkl"):
    """Train the model with synthetic data for demo purposes."""

    np.random.seed(42)
    n_samples = 10000

    data = {
        "flow_duration": np.random.exponential(1000, n_samples),
        "total_fwd_packets": np.random.poisson(20, n_samples),
        "total_bwd_packets": np.random.poisson(15, n_samples),
        "total_length_fwd_packets": np.random.exponential(5000, n_samples),
        "total_length_bwd_packets": np.random.exponential(3000, n_samples),
        "fwd_packet_length_mean": np.random.exponential(500, n_samples),
        "fwd_packet_length_std": np.random.exponential(200, n_samples),
        "bwd_packet_length_mean": np.random.exponential(400, n_samples),
        "bwd_packet_length_std": np.random.exponential(150, n_samples),
        "flow_bytes_per_sec": np.random.exponential(10000, n_samples),
        "flow_packets_per_sec": np.random.exponential(100, n_samples),
        "flow_iat_mean": np.random.exponential(500, n_samples),
        "flow_iat_std": np.random.exponential(200, n_samples),
        "flow_iat_max": np.random.exponential(2000, n_samples),
        "fwd_iat_total": np.random.exponential(1000, n_samples),
        "fwd_iat_mean": np.random.exponential(500, n_samples),
        "fwd_iat_std": np.random.exponential(200, n_samples),
        "bwd_iat_total": np.random.exponential(800, n_samples),
        "bwd_iat_mean": np.random.exponential(400, n_samples),
        "bwd_iat_std": np.random.exponential(150, n_samples),
        "fwd_packets_per_sec": np.random.exponential(50, n_samples),
        "bwd_packets_per_sec": np.random.exponential(40, n_samples),
        "down_up_ratio": np.random.exponential(2, n_samples),
        "avg_packet_size": np.random.exponential(500, n_samples),
        "avg_fwd_segment_size": np.random.exponential(500, n_samples),
        "avg_bwd_segment_size": np.random.exponential(400, n_samples),
        "subflow_fwd_packets": np.random.poisson(20, n_samples),
        "subflow_bwd_packets": np.random.poisson(15, n_samples),
        "subflow_fwd_bytes": np.random.exponential(5000, n_samples),
        "subflow_bwd_bytes": np.random.exponential(3000, n_samples),
    }

    df = pd.DataFrame(data)

    labels = []
    for i in range(n_samples):
        if i < n_samples * 0.97:
            labels.append("Normal")
        else:
            attack_types = ["DoS", "Port Scan", "Brute Force", "Data Exfiltration"]
            labels.append(np.random.choice(attack_types))

    df["Label"] = labels

    print(f"Training with {n_samples} samples")
    print(f"Label distribution: {df['Label'].value_counts().to_dict()}")

    label_mapping = get_label_mapping()
    classifier = NIDSClassifier(label_mapping)

    X = engineer_features(df)
    y = np.array([label_mapping.get(map_labels(l), 0) for l in df["Label"].values])

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Label distribution: {np.bincount(y)}")

    results = classifier.train(X.values, y, test_size=0.2, use_smote=True)

    classifier.save(output_path)

    print(f"\n✓ Model trained and saved to {output_path}")
    print(f"✓ Macro F1 Score: {results['f1_macro']:.4f}")

    return classifier, results


if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)
    train_with_synthetic_data()
