"""Performance metrics and monitoring utilities."""

import time
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading


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
