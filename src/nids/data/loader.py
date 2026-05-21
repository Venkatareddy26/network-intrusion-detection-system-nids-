from typing import Dict

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "flow_duration",
    "total_fwd_packets",
    "total_bwd_packets",
    "total_length_fwd_packets",
    "total_length_bwd_packets",
    "fwd_packet_length_mean",
    "fwd_packet_length_std",
    "bwd_packet_length_mean",
    "bwd_packet_length_std",
    "flow_bytes_per_sec",
    "flow_packets_per_sec",
    "flow_iat_mean",
    "flow_iat_std",
    "flow_iat_max",
    "fwd_iat_total",
    "fwd_iat_mean",
    "fwd_iat_std",
    "bwd_iat_total",
    "bwd_iat_mean",
    "bwd_iat_std",
    "fwd_packets_per_sec",
    "bwd_packets_per_sec",
    "down_up_ratio",
    "avg_packet_size",
    "avg_fwd_segment_size",
    "avg_bwd_segment_size",
    "subflow_fwd_packets",
    "subflow_bwd_packets",
    "subflow_fwd_bytes",
    "subflow_bwd_bytes",
]

ATTACK_LABELS = {
    "BENIGN": "Normal",
    "DoS Slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "Heartbleed": "DoS",
    "PortScan": "Port Scan",
    "Brute Force": "Brute Force",
    "FTP-Patator": "Brute Force",
    "SSH-Patator": "Brute Force",
    "Infiltration": "Data Exfiltration",
    "Web Attack": "Data Exfiltration",
}

NORMAL_LABELS = ["Normal"]
ATTACK_CATEGORIES = ["DoS", "Port Scan", "Brute Force", "Data Exfiltration"]


def load_cicids2017(filepath: str, sample_size: int = 0) -> pd.DataFrame:
    """Load CICIDS2017 dataset with optional sampling."""
    print(f"Loading dataset from {filepath}...")
    df = pd.read_csv(filepath, low_memory=False)
    df.columns = df.columns.str.strip()

    if sample_size > 0:
        df = df.sample(n=min(sample_size, len(df)), random_state=42)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features from raw network flow data."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)

    if "Flow Duration" in df.columns:
        df["flow_duration"] = df["Flow Duration"]
    if "Total Fwd Packets" in df.columns:
        df["total_fwd_packets"] = df["Total Fwd Packets"]
    if "Total Backward Packets" in df.columns:
        df["total_bwd_packets"] = df["Total Backward Packets"]
    if "Total Length of Fwd Packets" in df.columns:
        df["total_length_fwd_packets"] = df["Total Length of Fwd Packets"]
    if "Total Length of Bwd Packets" in df.columns:
        df["total_length_bwd_packets"] = df["Total Length of Bwd Packets"]
    if "Fwd Packet Length Mean" in df.columns:
        df["fwd_packet_length_mean"] = df["Fwd Packet Length Mean"]
    if "Fwd Packet Length Std" in df.columns:
        df["fwd_packet_length_std"] = df["Fwd Packet Length Std"]
    if "Bwd Packet Length Mean" in df.columns:
        df["bwd_packet_length_mean"] = df["Bwd Packet Length Mean"]
    if "Bwd Packet Length Std" in df.columns:
        df["bwd_packet_length_std"] = df["Bwd Packet Length Std"]
    if "Flow Bytes/s" in df.columns:
        df["flow_bytes_per_sec"] = df["Flow Bytes/s"]
    if "Flow Packets/s" in df.columns:
        df["flow_packets_per_sec"] = df["Flow Packets/s"]
    if "Flow IAT Mean" in df.columns:
        df["flow_iat_mean"] = df["Flow IAT Mean"]
    if "Flow IAT Std" in df.columns:
        df["flow_iat_std"] = df["Flow IAT Std"]
    if "Flow IAT Max" in df.columns:
        df["flow_iat_max"] = df["Flow IAT Max"]
    if "Fwd IAT Total" in df.columns:
        df["fwd_iat_total"] = df["Fwd IAT Total"]
    if "Fwd IAT Mean" in df.columns:
        df["fwd_iat_mean"] = df["Fwd IAT Mean"]
    if "Fwd IAT Std" in df.columns:
        df["fwd_iat_std"] = df["Fwd IAT Std"]
    if "Bwd IAT Total" in df.columns:
        df["bwd_iat_total"] = df["Bwd IAT Total"]
    if "Bwd IAT Mean" in df.columns:
        df["bwd_iat_mean"] = df["Bwd IAT Mean"]
    if "Bwd IAT Std" in df.columns:
        df["bwd_iat_std"] = df["Bwd IAT Std"]
    if "Fwd Packets/s" in df.columns:
        df["fwd_packets_per_sec"] = df["Fwd Packets/s"]
    if "Bwd Packets/s" in df.columns:
        df["bwd_packets_per_sec"] = df["Bwd Packets/s"]
    if "Down/Up Ratio" in df.columns:
        df["down_up_ratio"] = df["Down/Up Ratio"]
    if "Average Packet Size" in df.columns:
        df["avg_packet_size"] = df["Average Packet Size"]
    if "Avg Fwd Segment Size" in df.columns:
        df["avg_fwd_segment_size"] = df["Avg Fwd Segment Size"]
    if "Avg Bwd Segment Size" in df.columns:
        df["avg_bwd_segment_size"] = df["Avg Bwd Segment Size"]
    if "Subflow Fwd Packets" in df.columns:
        df["subflow_fwd_packets"] = df["Subflow Fwd Packets"]
    if "Subflow Bwd Packets" in df.columns:
        df["subflow_bwd_packets"] = df["Subflow Bwd Packets"]
    if "Subflow Fwd Bytes" in df.columns:
        df["subflow_fwd_bytes"] = df["Subflow Fwd Bytes"]
    if "Subflow Bwd Bytes" in df.columns:
        df["subflow_bwd_bytes"] = df["Subflow Bwd Bytes"]

    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    return df[FEATURE_COLUMNS]  # type: ignore[return-value]


def map_labels(label: str) -> str:
    """Map raw labels to attack categories."""
    label = str(label).strip()
    normalized = label.lower()

    if label in NORMAL_LABELS or normalized == "benign":
        return "Normal"

    if normalized.startswith("dos") or normalized in {"ddos", "heartbleed"}:
        return "DoS"
    if normalized in {"portscan", "port scan"}:
        return "Port Scan"
    if "patator" in normalized or "brute force" in normalized:
        return "Brute Force"
    if (
        normalized.startswith("web attack")
        or normalized in {"infiltration", "bot"}
        or "sql injection" in normalized
        or "xss" in normalized
    ):
        return "Data Exfiltration"

    return ATTACK_LABELS.get(label, "Data Exfiltration")


def get_label_mapping() -> Dict[str, int]:
    """Get label encoding mapping."""
    all_labels = ["Normal"] + ATTACK_CATEGORIES
    return {label: idx for idx, label in enumerate(all_labels)}
