"""Performance metrics data models for stress testing."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

import numpy as np


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics from stress testing.

    This class collects and aggregates performance data during stress testing,
    including latency, throughput, accuracy, and memory metrics.
    """

    # Latency metrics (milliseconds)
    latencies: List[float] = field(default_factory=list)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_mean: float = 0.0
    latency_std: float = 0.0

    # Throughput metrics
    throughput_fps: float = 0.0  # flows per second
    total_flows: int = 0
    duration_seconds: float = 0.0

    # Accuracy metrics
    fpr: float = 0.0  # False Positive Rate
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # Memory metrics (MB)
    memory_peak: float = 0.0
    memory_mean: float = 0.0
    memory_samples: List[float] = field(default_factory=list)

    # Attack distribution
    attack_counts: Dict[str, int] = field(default_factory=dict)

    # Timestamp
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_latency(self, latency_ms: float) -> None:
        """Add a latency measurement.

        Args:
            latency_ms: Latency in milliseconds
        """
        if latency_ms >= 0:
            self.latencies.append(latency_ms)

    def add_memory_sample(self, memory_mb: float) -> None:
        """Add a memory usage sample.

        Args:
            memory_mb: Memory usage in megabytes
        """
        if memory_mb >= 0:
            self.memory_samples.append(memory_mb)

    def calculate_statistics(self) -> None:
        """Calculate aggregate statistics from collected metrics."""
        # Latency statistics
        if self.latencies:
            latencies_array = np.array(self.latencies)
            self.latency_p50 = float(np.percentile(latencies_array, 50))
            self.latency_p95 = float(np.percentile(latencies_array, 95))
            self.latency_p99 = float(np.percentile(latencies_array, 99))
            self.latency_mean = float(np.mean(latencies_array))
            self.latency_std = float(np.std(latencies_array))

        # Memory statistics
        if self.memory_samples:
            memory_array = np.array(self.memory_samples)
            self.memory_peak = float(np.max(memory_array))
            self.memory_mean = float(np.mean(memory_array))

        # Throughput calculation
        if self.duration_seconds > 0:
            self.throughput_fps = self.total_flows / self.duration_seconds

    def get_percentile(self, p: int) -> float:
        """Get a specific percentile of latency measurements.

        Args:
            p: Percentile value (0-100)

        Returns:
            Latency value at the specified percentile
        """
        if not self.latencies:
            return 0.0
        return float(np.percentile(np.array(self.latencies), p))

    def get_summary(self) -> Dict[str, Any]:
        """Return summary dictionary for reporting.

        Returns:
            Dictionary containing all metrics
        """
        return {
            "timestamp": self.timestamp,
            "latency": {
                "p50_ms": self.latency_p50,
                "p95_ms": self.latency_p95,
                "p99_ms": self.latency_p99,
                "mean_ms": self.latency_mean,
                "std_ms": self.latency_std,
                "samples": len(self.latencies),
            },
            "throughput": {
                "flows_per_second": self.throughput_fps,
                "total_flows": self.total_flows,
                "duration_seconds": self.duration_seconds,
            },
            "accuracy": {
                "fpr": self.fpr,
                "accuracy": self.accuracy,
                "precision": self.precision,
                "recall": self.recall,
                "f1_score": self.f1_score,
            },
            "memory": {
                "peak_mb": self.memory_peak,
                "mean_mb": self.memory_mean,
                "samples": len(self.memory_samples),
            },
            "attack_distribution": self.attack_counts,
        }

    def meets_targets(self) -> bool:
        """Check if metrics meet production targets.

        Production targets:
        - p95 latency < 50ms
        - FPR < 2%
        - Throughput >= 100,000 flows/sec

        Returns:
            True if all targets are met, False otherwise
        """
        return (
            self.latency_p95 < 50.0 and
            self.fpr < 0.02 and
            self.throughput_fps >= 100000
        )

    def __repr__(self) -> str:
        """String representation of metrics."""
        return (
            f"PerformanceMetrics("
            f"p95={self.latency_p95:.2f}ms, "
            f"fpr={self.fpr:.4f}, "
            f"throughput={self.throughput_fps:.0f} fps, "
            f"flows={self.total_flows})"
        )
