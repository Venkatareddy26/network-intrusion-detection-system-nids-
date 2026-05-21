"""Performance metrics and monitoring utilities."""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from prometheus_client import CollectorRegistry, Gauge, generate_latest


@dataclass
class PerformanceMetrics:
    """Performance metrics tracker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_inference_time_ms: float = 0.0
    inference_times: List[float] = field(default_factory=list)
    max_inference_time_ms: float = 0.0
    min_inference_time_ms: float = float("inf")
    start_time: datetime = field(default_factory=datetime.utcnow)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_inference(self, duration_ms: float, success: bool = True):
        """Record an inference operation.

        Args:
            duration_ms: Inference duration in milliseconds
            success: Whether the inference was successful
        """
        with self._lock:
            self.total_requests += 1
            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            self.total_inference_time_ms += duration_ms
            self.inference_times.append(duration_ms)

            # Keep only last 10000 measurements
            if len(self.inference_times) > 10000:
                self.inference_times = self.inference_times[-10000:]

            self.max_inference_time_ms = max(self.max_inference_time_ms, duration_ms)
            self.min_inference_time_ms = min(self.min_inference_time_ms, duration_ms)

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics.

        Returns:
            Dictionary of statistics
        """
        with self._lock:
            if not self.inference_times:
                return {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "success_rate": 0.0,
                    "avg_inference_time_ms": 0.0,
                    "p50_inference_time_ms": 0.0,
                    "p95_inference_time_ms": 0.0,
                    "p99_inference_time_ms": 0.0,
                    "max_inference_time_ms": 0.0,
                    "min_inference_time_ms": 0.0,
                    "uptime_seconds": 0,
                }

            sorted_times = sorted(self.inference_times)
            n = len(sorted_times)

            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0,
                "avg_inference_time_ms": self.total_inference_time_ms / len(self.inference_times),
                "p50_inference_time_ms": sorted_times[int(n * 0.5)],
                "p95_inference_time_ms": sorted_times[int(n * 0.95)],
                "p99_inference_time_ms": sorted_times[int(n * 0.99)],
                "max_inference_time_ms": self.max_inference_time_ms,
                "min_inference_time_ms": self.min_inference_time_ms if self.min_inference_time_ms != float("inf") else 0.0,
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.total_requests = 0
            self.successful_requests = 0
            self.failed_requests = 0
            self.total_inference_time_ms = 0.0
            self.inference_times = []
            self.max_inference_time_ms = 0.0
            self.min_inference_time_ms = float("inf")
            self.start_time = datetime.utcnow()


class MetricsCollector:
    """Global metrics collector."""

    def __init__(self):
        self.performance = PerformanceMetrics()
        self.attack_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def record_attack(self, attack_type: str):
        """Record an attack detection.

        Args:
            attack_type: Type of attack detected
        """
        with self._lock:
            self.attack_counts[attack_type] = self.attack_counts.get(attack_type, 0) + 1

    def get_attack_distribution(self) -> Dict[str, int]:
        """Get attack type distribution.

        Returns:
            Dictionary of attack counts
        """
        with self._lock:
            return self.attack_counts.copy()

    def reset_attack_counts(self):
        """Reset attack counters."""
        with self._lock:
            self.attack_counts = {}


# Global metrics instance
metrics_collector = MetricsCollector()


def render_prometheus_metrics() -> bytes:
    """Render the current in-memory metrics in Prometheus text format."""
    registry = CollectorRegistry()
    stats = metrics_collector.performance.get_stats()

    scalar_metrics = {
        "nids_requests": (
            "Total inference requests handled by this process.",
            stats["total_requests"],
        ),
        "nids_successful_requests": (
            "Successful inference requests handled by this process.",
            stats["successful_requests"],
        ),
        "nids_failed_requests": (
            "Failed inference requests handled by this process.",
            stats["failed_requests"],
        ),
        "nids_success_rate": (
            "Successful inference request ratio for this process.",
            stats["success_rate"],
        ),
        "nids_avg_inference_time_ms": (
            "Average inference latency in milliseconds.",
            stats["avg_inference_time_ms"],
        ),
        "nids_p50_inference_time_ms": (
            "Median inference latency in milliseconds.",
            stats["p50_inference_time_ms"],
        ),
        "nids_p95_inference_time_ms": (
            "95th percentile inference latency in milliseconds.",
            stats["p95_inference_time_ms"],
        ),
        "nids_p99_inference_time_ms": (
            "99th percentile inference latency in milliseconds.",
            stats["p99_inference_time_ms"],
        ),
        "nids_uptime_seconds": (
            "Seconds since the in-memory metrics collector was initialized.",
            stats["uptime_seconds"],
        ),
    }

    for name, (description, value) in scalar_metrics.items():
        gauge = Gauge(name, description, registry=registry)
        gauge.set(float(value))

    attack_gauge = Gauge(
        "nids_attacks_detected",
        "Detected attacks by normalized attack type.",
        ["attack_type"],
        registry=registry,
    )
    for attack_type, count in metrics_collector.get_attack_distribution().items():
        attack_gauge.labels(attack_type=attack_type).set(float(count))

    return generate_latest(registry)
