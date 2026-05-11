"""Generate synthetic network flow data for training and testing."""

import numpy as np
import pandas as pd
from typing import Dict


def generate_dataset(
    n_normal: int = 50000,
    n_dos: int = 2000,
    n_portscan: int = 1500,
    n_bruteforce: int = 1000,
    n_exfil: int = 500,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic network flow dataset.
    
    Args:
        n_normal: Number of normal traffic samples
        n_dos: Number of DoS attack samples
        n_portscan: Number of port scan samples
        n_bruteforce: Number of brute force samples
        n_exfil: Number of data exfiltration samples
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with network flow features and labels
    """
    np.random.seed(seed)
    
    samples = []
    
    # Generate Normal traffic
    for _ in range(n_normal):
        samples.append(_generate_normal_flow())
    
    # Generate DoS attacks
    for _ in range(n_dos):
        samples.append(_generate_dos_flow())
    
    # Generate Port Scans
    for _ in range(n_portscan):
        samples.append(_generate_portscan_flow())
    
    # Generate Brute Force attacks
    for _ in range(n_bruteforce):
        samples.append(_generate_bruteforce_flow())
    
    # Generate Data Exfiltration
    for _ in range(n_exfil):
        samples.append(_generate_exfil_flow())
    
    df = pd.DataFrame(samples)
    
    # Shuffle
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    
    return df


def _generate_normal_flow() -> Dict:
    """Generate normal traffic flow."""
    flow_duration = np.random.exponential(5000)
    fwd_packets = np.random.poisson(20)
    bwd_packets = np.random.poisson(15)
    
    return {
        "flow_duration": flow_duration,
        "total_fwd_packets": fwd_packets,
        "total_bwd_packets": bwd_packets,
        "total_length_fwd_packets": fwd_packets * np.random.exponential(500),
        "total_length_bwd_packets": bwd_packets * np.random.exponential(400),
        "fwd_packet_length_mean": np.random.exponential(500),
        "fwd_packet_length_std": np.random.exponential(200),
        "bwd_packet_length_mean": np.random.exponential(400),
        "bwd_packet_length_std": np.random.exponential(150),
        "flow_bytes_per_sec": np.random.exponential(10000),
        "flow_packets_per_sec": np.random.exponential(50),
        "flow_iat_mean": np.random.exponential(500),
        "flow_iat_std": np.random.exponential(200),
        "flow_iat_max": np.random.exponential(2000),
        "fwd_iat_total": np.random.exponential(1000),
        "fwd_iat_mean": np.random.exponential(500),
        "fwd_iat_std": np.random.exponential(200),
        "bwd_iat_total": np.random.exponential(800),
        "bwd_iat_mean": np.random.exponential(400),
        "bwd_iat_std": np.random.exponential(150),
        "fwd_packets_per_sec": np.random.exponential(25),
        "bwd_packets_per_sec": np.random.exponential(20),
        "down_up_ratio": np.random.uniform(0.5, 2.0),
        "avg_packet_size": np.random.exponential(500),
        "avg_fwd_segment_size": np.random.exponential(500),
        "avg_bwd_segment_size": np.random.exponential(400),
        "subflow_fwd_packets": fwd_packets,
        "subflow_bwd_packets": bwd_packets,
        "subflow_fwd_bytes": fwd_packets * np.random.exponential(500),
        "subflow_bwd_bytes": bwd_packets * np.random.exponential(400),
        "Label": "Normal",
    }


def _generate_dos_flow() -> Dict:
    """Generate DoS attack flow (high packet rate, low response)."""
    flow_duration = np.random.exponential(1000)
    fwd_packets = np.random.randint(100, 10000)
    bwd_packets = np.random.randint(0, 10)
    
    return {
        "flow_duration": flow_duration,
        "total_fwd_packets": fwd_packets,
        "total_bwd_packets": bwd_packets,
        "total_length_fwd_packets": fwd_packets * np.random.exponential(100),
        "total_length_bwd_packets": bwd_packets * np.random.exponential(50),
        "fwd_packet_length_mean": np.random.exponential(100),
        "fwd_packet_length_std": np.random.exponential(50),
        "bwd_packet_length_mean": np.random.exponential(50),
        "bwd_packet_length_std": np.random.exponential(20),
        "flow_bytes_per_sec": np.random.uniform(50000, 200000),
        "flow_packets_per_sec": np.random.uniform(500, 5000),
        "flow_iat_mean": np.random.exponential(10),
        "flow_iat_std": np.random.exponential(5),
        "flow_iat_max": np.random.exponential(100),
        "fwd_iat_total": np.random.exponential(100),
        "fwd_iat_mean": np.random.exponential(10),
        "fwd_iat_std": np.random.exponential(5),
        "bwd_iat_total": np.random.exponential(50),
        "bwd_iat_mean": np.random.exponential(20),
        "bwd_iat_std": np.random.exponential(10),
        "fwd_packets_per_sec": np.random.uniform(500, 5000),
        "bwd_packets_per_sec": np.random.uniform(0, 10),
        "down_up_ratio": np.random.uniform(0.0, 0.1),
        "avg_packet_size": np.random.exponential(100),
        "avg_fwd_segment_size": np.random.exponential(100),
        "avg_bwd_segment_size": np.random.exponential(50),
        "subflow_fwd_packets": fwd_packets,
        "subflow_bwd_packets": bwd_packets,
        "subflow_fwd_bytes": fwd_packets * np.random.exponential(100),
        "subflow_bwd_bytes": bwd_packets * np.random.exponential(50),
        "Label": "DoS",
    }


def _generate_portscan_flow() -> Dict:
    """Generate port scan flow (many connections, small packets)."""
    flow_duration = np.random.exponential(100)
    fwd_packets = np.random.randint(1, 10)
    bwd_packets = np.random.randint(0, 5)
    
    return {
        "flow_duration": flow_duration,
        "total_fwd_packets": fwd_packets,
        "total_bwd_packets": bwd_packets,
        "total_length_fwd_packets": fwd_packets * np.random.exponential(50),
        "total_length_bwd_packets": bwd_packets * np.random.exponential(50),
        "fwd_packet_length_mean": np.random.exponential(50),
        "fwd_packet_length_std": np.random.exponential(20),
        "bwd_packet_length_mean": np.random.exponential(50),
        "bwd_packet_length_std": np.random.exponential(20),
        "flow_bytes_per_sec": np.random.uniform(100, 1000),
        "flow_packets_per_sec": np.random.uniform(10, 100),
        "flow_iat_mean": np.random.exponential(50),
        "flow_iat_std": np.random.exponential(20),
        "flow_iat_max": np.random.exponential(200),
        "fwd_iat_total": np.random.exponential(100),
        "fwd_iat_mean": np.random.exponential(50),
        "fwd_iat_std": np.random.exponential(20),
        "bwd_iat_total": np.random.exponential(50),
        "bwd_iat_mean": np.random.exponential(30),
        "bwd_iat_std": np.random.exponential(15),
        "fwd_packets_per_sec": np.random.uniform(10, 100),
        "bwd_packets_per_sec": np.random.uniform(0, 10),
        "down_up_ratio": np.random.uniform(0.0, 0.5),
        "avg_packet_size": np.random.exponential(50),
        "avg_fwd_segment_size": np.random.exponential(50),
        "avg_bwd_segment_size": np.random.exponential(50),
        "subflow_fwd_packets": fwd_packets,
        "subflow_bwd_packets": bwd_packets,
        "subflow_fwd_bytes": fwd_packets * np.random.exponential(50),
        "subflow_bwd_bytes": bwd_packets * np.random.exponential(50),
        "Label": "Port Scan",
    }


def _generate_bruteforce_flow() -> Dict:
    """Generate brute force attack flow (repeated login attempts)."""
    flow_duration = np.random.exponential(3000)
    fwd_packets = np.random.randint(20, 200)
    bwd_packets = np.random.randint(10, 100)
    
    return {
        "flow_duration": flow_duration,
        "total_fwd_packets": fwd_packets,
        "total_bwd_packets": bwd_packets,
        "total_length_fwd_packets": fwd_packets * np.random.exponential(300),
        "total_length_bwd_packets": bwd_packets * np.random.exponential(200),
        "fwd_packet_length_mean": np.random.exponential(300),
        "fwd_packet_length_std": np.random.exponential(100),
        "bwd_packet_length_mean": np.random.exponential(200),
        "bwd_packet_length_std": np.random.exponential(80),
        "flow_bytes_per_sec": np.random.uniform(2000, 10000),
        "flow_packets_per_sec": np.random.uniform(20, 100),
        "flow_iat_mean": np.random.exponential(200),
        "flow_iat_std": np.random.exponential(100),
        "flow_iat_max": np.random.exponential(1000),
        "fwd_iat_total": np.random.exponential(500),
        "fwd_iat_mean": np.random.exponential(200),
        "fwd_iat_std": np.random.exponential(100),
        "bwd_iat_total": np.random.exponential(400),
        "bwd_iat_mean": np.random.exponential(150),
        "bwd_iat_std": np.random.exponential(80),
        "fwd_packets_per_sec": np.random.uniform(20, 100),
        "bwd_packets_per_sec": np.random.uniform(10, 50),
        "down_up_ratio": np.random.uniform(0.3, 0.8),
        "avg_packet_size": np.random.exponential(300),
        "avg_fwd_segment_size": np.random.exponential(300),
        "avg_bwd_segment_size": np.random.exponential(200),
        "subflow_fwd_packets": fwd_packets,
        "subflow_bwd_packets": bwd_packets,
        "subflow_fwd_bytes": fwd_packets * np.random.exponential(300),
        "subflow_bwd_bytes": bwd_packets * np.random.exponential(200),
        "Label": "Brute Force",
    }


def _generate_exfil_flow() -> Dict:
    """Generate data exfiltration flow (large outbound data)."""
    flow_duration = np.random.exponential(10000)
    fwd_packets = np.random.randint(50, 500)
    bwd_packets = np.random.randint(10, 100)
    
    return {
        "flow_duration": flow_duration,
        "total_fwd_packets": fwd_packets,
        "total_bwd_packets": bwd_packets,
        "total_length_fwd_packets": fwd_packets * np.random.exponential(1000),
        "total_length_bwd_packets": bwd_packets * np.random.exponential(200),
        "fwd_packet_length_mean": np.random.exponential(1000),
        "fwd_packet_length_std": np.random.exponential(300),
        "bwd_packet_length_mean": np.random.exponential(200),
        "bwd_packet_length_std": np.random.exponential(100),
        "flow_bytes_per_sec": np.random.uniform(20000, 100000),
        "flow_packets_per_sec": np.random.uniform(50, 200),
        "flow_iat_mean": np.random.exponential(300),
        "flow_iat_std": np.random.exponential(150),
        "flow_iat_max": np.random.exponential(2000),
        "fwd_iat_total": np.random.exponential(1000),
        "fwd_iat_mean": np.random.exponential(300),
        "fwd_iat_std": np.random.exponential(150),
        "bwd_iat_total": np.random.exponential(500),
        "bwd_iat_mean": np.random.exponential(200),
        "bwd_iat_std": np.random.exponential(100),
        "fwd_packets_per_sec": np.random.uniform(50, 200),
        "bwd_packets_per_sec": np.random.uniform(10, 50),
        "down_up_ratio": np.random.uniform(0.1, 0.3),
        "avg_packet_size": np.random.exponential(800),
        "avg_fwd_segment_size": np.random.exponential(1000),
        "avg_bwd_segment_size": np.random.exponential(200),
        "subflow_fwd_packets": fwd_packets,
        "subflow_bwd_packets": bwd_packets,
        "subflow_fwd_bytes": fwd_packets * np.random.exponential(1000),
        "subflow_bwd_bytes": bwd_packets * np.random.exponential(200),
        "Label": "Data Exfiltration",
    }
