"""Measurement utilities for latency, throughput, and memory tracking."""

import time
from contextlib import contextmanager
from typing import Any, Callable, List, Tuple

import numpy as np
import psutil

from src.nids.utils.logging import get_logger

logger = get_logger(__name__)


class LatencyMeasurement:
    """Utility for measuring inference latency."""

    @staticmethod
    def measure_single(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """Measure latency of a single function call.

        Args:
            func: Function to measure
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Tuple of (function result, latency in milliseconds)
        """
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        return result, latency_ms

    @staticmethod
    def measure_batch(
        func: Callable,
        data: np.ndarray,
        batch_size: int = 1
    ) -> List[float]:
        """Measure latency for batch processing.

        Args:
            func: Function to measure (should accept numpy array)
            data: Input data array
            batch_size: Size of each batch

        Returns:
            List of latency measurements in milliseconds
        """
        latencies = []
        total_samples = len(data)

        for start_idx in range(0, total_samples, batch_size):
            end_idx = min(start_idx + batch_size, total_samples)
            batch = data[start_idx:end_idx]

            start_time = time.perf_counter()
            func(batch)
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

        return latencies

    @staticmethod
    @contextmanager
    def timer(name: str = "Operation"):
        """Context manager for timing operations.

        Args:
            name: Name of the operation being timed

        Yields:
            Dictionary that will contain the elapsed time

        Example:
            with LatencyMeasurement.timer("inference") as t:
                model.predict(X)
            print(f"Took {t['elapsed_ms']:.2f}ms")
        """
        timing = {}
        start_time = time.perf_counter()

        try:
            yield timing
        finally:
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000
            timing['elapsed_ms'] = elapsed_ms
            timing['elapsed_s'] = elapsed_ms / 1000
            logger.debug(f"{name} took {elapsed_ms:.2f}ms")


class ThroughputMeasurement:
    """Utility for measuring processing throughput."""

    @staticmethod
    def measure(
        func: Callable,
        data: np.ndarray,
        warmup_runs: int = 3
    ) -> float:
        """Measure throughput in items per second.

        Args:
            func: Function to measure (should accept numpy array)
            data: Input data array
            warmup_runs: Number of warmup runs before measurement

        Returns:
            Throughput in items per second
        """
        # Warmup runs
        for _ in range(warmup_runs):
            func(data[:min(100, len(data))])

        # Actual measurement
        start_time = time.perf_counter()
        func(data)
        end_time = time.perf_counter()

        duration_s = end_time - start_time
        throughput = len(data) / duration_s if duration_s > 0 else 0.0

        logger.info(
            f"Processed {len(data)} items in {duration_s:.2f}s "
            f"({throughput:.0f} items/sec)"
        )

        return throughput

    @staticmethod
    def measure_with_duration(
        total_items: int,
        duration_seconds: float
    ) -> float:
        """Calculate throughput from total items and duration.

        Args:
            total_items: Total number of items processed
            duration_seconds: Total duration in seconds

        Returns:
            Throughput in items per second
        """
        if duration_seconds <= 0:
            return 0.0
        return total_items / duration_seconds


class MemoryTracker:
    """Utility for tracking memory usage during operations."""

    def __init__(self):
        """Initialize memory tracker."""
        self.samples: List[float] = []
        self.process = psutil.Process()

    def get_current_usage_mb(self) -> float:
        """Get current memory usage in megabytes.

        Returns:
            Memory usage in MB
        """
        return self.process.memory_info().rss / (1024 * 1024)

    def get_system_memory_percent(self) -> float:
        """Get system-wide memory usage percentage.

        Returns:
            Memory usage as percentage (0-100)
        """
        return psutil.virtual_memory().percent

    def sample(self) -> float:
        """Take a memory usage sample and store it.

        Returns:
            Current memory usage in MB
        """
        usage_mb = self.get_current_usage_mb()
        self.samples.append(usage_mb)
        return usage_mb

    def get_peak_mb(self) -> float:
        """Get peak memory usage from samples.

        Returns:
            Peak memory usage in MB
        """
        return max(self.samples) if self.samples else 0.0

    def get_mean_mb(self) -> float:
        """Get mean memory usage from samples.

        Returns:
            Mean memory usage in MB
        """
        return np.mean(self.samples) if self.samples else 0.0

    def get_samples(self) -> List[float]:
        """Get all memory samples.

        Returns:
            List of memory usage samples in MB
        """
        return self.samples.copy()

    def reset(self) -> None:
        """Reset memory samples."""
        self.samples.clear()

    @contextmanager
    def track(self, sample_interval_ms: int = 100):
        """Context manager for tracking memory during an operation.

        Args:
            sample_interval_ms: Interval between samples in milliseconds

        Yields:
            Self for accessing samples during operation

        Example:
            tracker = MemoryTracker()
            with tracker.track():
                # Do memory-intensive operation
                process_large_dataset()
            print(f"Peak memory: {tracker.get_peak_mb():.2f}MB")
        """
        import threading

        self.reset()
        stop_event = threading.Event()

        def sample_loop():
            while not stop_event.is_set():
                self.sample()
                time.sleep(sample_interval_ms / 1000)

        # Start sampling thread
        sample_thread = threading.Thread(target=sample_loop, daemon=True)
        sample_thread.start()

        try:
            yield self
        finally:
            stop_event.set()
            sample_thread.join(timeout=1.0)
            # Take final sample
            self.sample()


class AccuracyMeasurement:
    """Utility for measuring classification accuracy metrics."""

    @staticmethod
    def calculate_fpr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate False Positive Rate.

        FPR = FP / (FP + TN)

        Args:
            y_true: True labels
            y_pred: Predicted labels

        Returns:
            False Positive Rate (0.0 to 1.0)
        """
        # Assuming 0 is the normal/negative class
        # False Positives: predicted attack (non-zero) but actually normal (0)
        fp = np.sum((y_pred != 0) & (y_true == 0))

        # True Negatives: predicted normal (0) and actually normal (0)
        tn = np.sum((y_pred == 0) & (y_true == 0))

        denominator = fp + tn
        if denominator == 0:
            return 0.0

        fpr = fp / denominator
        logger.debug(f"FPR calculation: FP={fp}, TN={tn}, FPR={fpr:.4f}")

        return float(fpr)

    @staticmethod
    def calculate_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> dict:
        """Calculate comprehensive accuracy metrics.

        Args:
            y_true: True labels
            y_pred: Predicted labels

        Returns:
            Dictionary with accuracy, precision, recall, f1, and fpr
        """
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

        # Calculate standard metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average='macro', zero_division=0)
        recall = recall_score(y_true, y_pred, average='macro', zero_division=0)
        f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)

        # Calculate FPR
        fpr = AccuracyMeasurement.calculate_fpr(y_true, y_pred)

        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'fpr': float(fpr),
        }
