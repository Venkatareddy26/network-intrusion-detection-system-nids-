import json
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np


@dataclass
class NetworkFlow:
    """Represents a single network flow."""

    timestamp: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    flow_duration: float
    total_fwd_packets: int
    total_bwd_packets: int
    total_length_fwd_packets: float
    total_length_bwd_packets: float
    fwd_packet_length_mean: float
    fwd_packet_length_std: float
    bwd_packet_length_mean: float
    bwd_packet_length_std: float
    flow_bytes_per_sec: float
    flow_packets_per_sec: float
    flow_iat_mean: float
    flow_iat_std: float
    flow_iat_max: float
    fwd_iat_total: float
    fwd_iat_mean: float
    fwd_iat_std: float
    bwd_iat_total: float
    bwd_iat_mean: float
    bwd_iat_std: float
    fwd_packets_per_sec: float
    bwd_packets_per_sec: float
    down_up_ratio: float
    avg_packet_size: float
    avg_fwd_segment_size: float
    avg_bwd_segment_size: float
    subflow_fwd_packets: int
    subflow_bwd_packets: int
    subflow_fwd_bytes: float
    subflow_bwd_bytes: float

    def to_features(self) -> np.ndarray:
        """Extract feature vector for inference."""
        return np.array(
            [
                self.flow_duration,
                self.total_fwd_packets,
                self.total_bwd_packets,
                self.total_length_fwd_packets,
                self.total_length_bwd_packets,
                self.fwd_packet_length_mean,
                self.fwd_packet_length_std,
                self.bwd_packet_length_mean,
                self.bwd_packet_length_std,
                self.flow_bytes_per_sec,
                self.flow_packets_per_sec,
                self.flow_iat_mean,
                self.flow_iat_std,
                self.flow_iat_max,
                self.fwd_iat_total,
                self.fwd_iat_mean,
                self.fwd_iat_std,
                self.bwd_iat_total,
                self.bwd_iat_mean,
                self.bwd_iat_std,
                self.fwd_packets_per_sec,
                self.bwd_packets_per_sec,
                self.down_up_ratio,
                self.avg_packet_size,
                self.avg_fwd_segment_size,
                self.avg_bwd_segment_size,
                self.subflow_fwd_packets,
                self.subflow_bwd_packets,
                self.subflow_fwd_bytes,
                self.subflow_bwd_bytes,
            ]
        )

    @staticmethod
    def from_dict(d: Dict) -> "NetworkFlow":
        """Create NetworkFlow from dictionary."""
        return NetworkFlow(**d)


@dataclass
class Alert:
    """Represents a security alert."""

    id: str
    timestamp: str
    src_ip: str
    dst_ip: str
    attack_type: str
    confidence: float
    top_3_features: List[Dict[str, Any]]
    severity: str

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class AlertQueue:
    """Thread-safe queue for alerts."""

    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.queue = deque(maxlen=maxsize)
        self._lock = threading.Lock()

    def put(self, alert: Alert, timeout: float = None):
        with self._lock:
            self.queue.append(alert)

    def get(self, timeout: float = None) -> Optional[Alert]:
        deadline = None if timeout is None else time.time() + timeout
        while True:
            with self._lock:
                if self.queue:
                    return self.queue.popleft()

            if timeout is None or (deadline is not None and time.time() >= deadline):
                return None
            time.sleep(0.01)

    def get_all(self) -> List[Alert]:
        with self._lock:
            return list(reversed(self.queue))

    def size(self) -> int:
        with self._lock:
            return len(self.queue)


class Pipeline:
    """Real-time NIDS pipeline for log ingestion and inference."""

    def __init__(self, classifier, explainer, alert_callback: Callable = None):
        self.classifier = classifier
        self.explainer = explainer
        self.alert_queue = AlertQueue()
        self.alert_callback = alert_callback
        self._running = False
        self._stats = {
            "total_flows": 0,
            "normal_flows": 0,
            "attack_flows": 0,
            "inference_times": [],
            "attack_distribution": {},
        }

    def process_flow(self, flow: NetworkFlow) -> Alert:
        """Process a single network flow."""
        start_time = time.time()

        features = flow.to_features()

        prediction = self.classifier.predict_single(features)

        inference_time = (time.time() - start_time) * 1000

        alert = None
        if prediction["prediction"] != "Normal":
            class_index = getattr(self.classifier, "label_mapping", {}).get(
                prediction["prediction"]
            )
            explanation = self.explainer.explain_prediction(
                features, top_k=3, class_index=class_index
            )

            severity = "high" if prediction["confidence"] > 0.8 else "medium"

            alert = Alert(
                id=f"alert_{self._stats['total_flows']}_{int(time.time() * 1000)}",
                timestamp=flow.timestamp,
                src_ip=flow.src_ip,
                dst_ip=flow.dst_ip,
                attack_type=prediction["prediction"],
                confidence=prediction["confidence"],
                top_3_features=explanation["top_features"],
                severity=severity,
            )

            self.alert_queue.put(alert)

            if self.alert_callback:
                self.alert_callback(alert)

        self._stats["total_flows"] += 1
        if prediction["prediction"] == "Normal":
            self._stats["normal_flows"] += 1
        else:
            self._stats["attack_flows"] += 1

        self._stats["inference_times"].append(inference_time)
        if len(self._stats["inference_times"]) > 10000:
            self._stats["inference_times"] = self._stats["inference_times"][-10000:]

        attack_type = prediction["prediction"]
        self._stats["attack_distribution"][attack_type] = (
            self._stats["attack_distribution"].get(attack_type, 0) + 1
        )

        return alert

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        avg_inference_time = 0
        latest_inference_time = 0
        p95_inference_time = 0
        inference_times = list(self._stats["inference_times"])
        if inference_times:
            avg_inference_time = sum(inference_times) / len(inference_times)
            latest_inference_time = inference_times[-1]
            sorted_times = sorted(inference_times)
            p95_index = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
            p95_inference_time = sorted_times[p95_index]

        return {
            "total_flows": self._stats["total_flows"],
            "normal_flows": self._stats["normal_flows"],
            "attack_flows": self._stats["attack_flows"],
            "avg_inference_time_ms": avg_inference_time,
            "latest_inference_time_ms": latest_inference_time,
            "p95_inference_time_ms": p95_inference_time,
            "inference_times": inference_times,
            "attack_distribution": self._stats["attack_distribution"],
            "pending_alerts": self.alert_queue.size(),
        }

    def reset_stats(self):
        """Reset pipeline statistics."""
        self._stats = {
            "total_flows": 0,
            "normal_flows": 0,
            "attack_flows": 0,
            "inference_times": [],
            "attack_distribution": {},
        }


def simulate_flow() -> NetworkFlow:
    """Generate a simulated network flow for demo purposes."""
    import random

    protocols = ["TCP", "UDP", "ICMP"]
    attack_types = ["Normal", "DoS", "Port Scan", "Brute Force", "Data Exfiltration"]

    is_attack = random.random() < 0.03

    if is_attack:
        attack = random.choice(attack_types[1:])
        if attack == "DoS":
            flow_duration = random.uniform(0, 1000)
            fwd_packets = random.randint(100, 10000)
            bwd_packets = random.randint(0, 10)
            bytes_per_sec = random.uniform(10000, 100000)
        elif attack == "Port Scan":
            flow_duration = random.uniform(0, 100)
            fwd_packets = random.randint(10, 100)
            bwd_packets = random.randint(0, 5)
            bytes_per_sec = random.uniform(100, 1000)
        elif attack == "Brute Force":
            flow_duration = random.uniform(1000, 5000)
            fwd_packets = random.randint(50, 200)
            bwd_packets = random.randint(10, 50)
            bytes_per_sec = random.uniform(1000, 5000)
        else:
            flow_duration = random.uniform(100, 1000)
            fwd_packets = random.randint(20, 200)
            bwd_packets = random.randint(5, 50)
            bytes_per_sec = random.uniform(500, 5000)
    else:
        attack = "Normal"
        flow_duration = random.uniform(100, 10000)
        fwd_packets = random.randint(5, 100)
        bwd_packets = random.randint(5, 100)
        bytes_per_sec = random.uniform(100, 10000)

    return NetworkFlow(
        timestamp=datetime.now().isoformat(),
        src_ip=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
        dst_ip=f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
        src_port=random.randint(1024, 65535),
        dst_port=random.choice([80, 443, 22, 3389, 8080]),
        protocol=random.choice(protocols),
        flow_duration=flow_duration,
        total_fwd_packets=fwd_packets,
        total_bwd_packets=bwd_packets,
        total_length_fwd_packets=fwd_packets * random.uniform(40, 1500),
        total_length_bwd_packets=bwd_packets * random.uniform(40, 1500),
        fwd_packet_length_mean=random.uniform(40, 1500),
        fwd_packet_length_std=random.uniform(0, 500),
        bwd_packet_length_mean=random.uniform(40, 1500),
        bwd_packet_length_std=random.uniform(0, 500),
        flow_bytes_per_sec=bytes_per_sec,
        flow_packets_per_sec=random.uniform(1, 1000),
        flow_iat_mean=random.uniform(0, 1000),
        flow_iat_std=random.uniform(0, 500),
        flow_iat_max=random.uniform(0, 5000),
        fwd_iat_total=random.uniform(0, 1000),
        fwd_iat_mean=random.uniform(0, 1000),
        fwd_iat_std=random.uniform(0, 500),
        bwd_iat_total=random.uniform(0, 1000),
        bwd_iat_mean=random.uniform(0, 1000),
        bwd_iat_std=random.uniform(0, 500),
        fwd_packets_per_sec=random.uniform(0, 100),
        bwd_packets_per_sec=random.uniform(0, 100),
        down_up_ratio=random.uniform(0.1, 10),
        avg_packet_size=random.uniform(40, 1500),
        avg_fwd_segment_size=random.uniform(40, 1500),
        avg_bwd_segment_size=random.uniform(40, 1500),
        subflow_fwd_packets=fwd_packets,
        subflow_bwd_packets=bwd_packets,
        subflow_fwd_bytes=fwd_packets * random.uniform(40, 1500),
        subflow_bwd_bytes=bwd_packets * random.uniform(40, 1500),
    )
