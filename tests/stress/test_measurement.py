"""Unit tests for measurement utilities."""

import time

import numpy as np
import pytest

from tests.stress.measurement import (
    AccuracyMeasurement,
    LatencyMeasurement,
    MemoryTracker,
    ThroughputMeasurement,
)


class TestLatencyMeasurement:
    """Test suite for LatencyMeasurement."""

    def test_measure_single(self):
        """Test measuring latency of a single function call."""
        def slow_function():
            time.sleep(0.01)  # 10ms
            return "result"

        result, latency_ms = LatencyMeasurement.measure_single(slow_function)

        assert result == "result"
        assert latency_ms >= 10.0  # Should be at least 10ms
        assert latency_ms < 50.0  # Should be less than 50ms

    def test_measure_single_with_args(self):
        """Test measuring function with arguments."""
        def add_numbers(a, b):
            return a + b

        result, latency_ms = LatencyMeasurement.measure_single(add_numbers, 5, 3)

        assert result == 8
        assert latency_ms >= 0

    def test_measure_single_with_kwargs(self):
        """Test measuring function with keyword arguments."""
        def multiply(x, y=2):
            return x * y

        result, latency_ms = LatencyMeasurement.measure_single(multiply, 5, y=3)

        assert result == 15
        assert latency_ms >= 0

    def test_measure_batch(self):
        """Test measuring batch processing latency."""
        data = np.arange(1000)

        def process_batch(batch):
            return np.sum(batch)

        latencies = LatencyMeasurement.measure_batch(
            process_batch, data, batch_size=100
        )

        assert len(latencies) == 10  # 1000 / 100 = 10 batches
        assert all(lat >= 0 for lat in latencies)

    def test_measure_batch_single_item(self):
        """Test measuring batch with batch_size=1."""
        data = np.arange(10)

        def process_batch(batch):
            return batch[0]

        latencies = LatencyMeasurement.measure_batch(
            process_batch, data, batch_size=1
        )

        assert len(latencies) == 10

    def test_timer_context_manager(self):
        """Test timer context manager."""
        with LatencyMeasurement.timer("test_operation") as t:
            time.sleep(0.01)  # 10ms

        assert "elapsed_ms" in t
        assert "elapsed_s" in t
        assert t["elapsed_ms"] >= 10.0
        assert t["elapsed_s"] >= 0.01

    def test_timer_with_exception(self):
        """Test timer context manager with exception."""
        with pytest.raises(ValueError):
            with LatencyMeasurement.timer("failing_operation") as t:
                raise ValueError("Test error")

        # Timer should still record elapsed time
        assert "elapsed_ms" in t


class TestThroughputMeasurement:
    """Test suite for ThroughputMeasurement."""

    def test_measure(self):
        """Test measuring throughput."""
        data = np.arange(1000)

        def process_data(arr):
            return np.sum(arr)

        throughput = ThroughputMeasurement.measure(process_data, data, warmup_runs=1)

        assert throughput > 0
        assert isinstance(throughput, float)

    def test_measure_with_warmup(self):
        """Test measuring throughput with warmup runs."""
        data = np.arange(5000)

        def process_data(arr):
            return np.mean(arr)

        throughput = ThroughputMeasurement.measure(
            process_data, data, warmup_runs=3
        )

        assert throughput > 0

    def test_measure_with_duration(self):
        """Test calculating throughput from duration."""
        throughput = ThroughputMeasurement.measure_with_duration(
            total_items=100000,
            duration_seconds=10.0
        )

        assert throughput == 10000.0

    def test_measure_with_duration_zero(self):
        """Test throughput calculation with zero duration."""
        throughput = ThroughputMeasurement.measure_with_duration(
            total_items=1000,
            duration_seconds=0.0
        )

        assert throughput == 0.0

    def test_measure_with_duration_negative(self):
        """Test throughput calculation with negative duration."""
        throughput = ThroughputMeasurement.measure_with_duration(
            total_items=1000,
            duration_seconds=-5.0
        )

        assert throughput == 0.0


class TestMemoryTracker:
    """Test suite for MemoryTracker."""

    def test_initialization(self):
        """Test MemoryTracker initialization."""
        tracker = MemoryTracker()

        assert tracker.samples == []
        assert tracker.process is not None

    def test_get_current_usage_mb(self):
        """Test getting current memory usage."""
        tracker = MemoryTracker()

        usage = tracker.get_current_usage_mb()

        assert isinstance(usage, float)
        assert usage > 0

    def test_get_system_memory_percent(self):
        """Test getting system memory percentage."""
        tracker = MemoryTracker()

        percent = tracker.get_system_memory_percent()

        assert isinstance(percent, float)
        assert 0 <= percent <= 100

    def test_sample(self):
        """Test taking a memory sample."""
        tracker = MemoryTracker()

        usage = tracker.sample()

        assert isinstance(usage, float)
        assert usage > 0
        assert len(tracker.samples) == 1
        assert tracker.samples[0] == usage

    def test_multiple_samples(self):
        """Test taking multiple memory samples."""
        tracker = MemoryTracker()

        tracker.sample()
        tracker.sample()
        tracker.sample()

        assert len(tracker.samples) == 3

    def test_get_peak_mb(self):
        """Test getting peak memory usage."""
        tracker = MemoryTracker()

        tracker.samples = [100.0, 150.0, 120.0, 200.0, 180.0]

        peak = tracker.get_peak_mb()

        assert peak == 200.0

    def test_get_peak_mb_empty(self):
        """Test getting peak with no samples."""
        tracker = MemoryTracker()

        peak = tracker.get_peak_mb()

        assert peak == 0.0

    def test_get_mean_mb(self):
        """Test getting mean memory usage."""
        tracker = MemoryTracker()

        tracker.samples = [100.0, 150.0, 200.0]

        mean = tracker.get_mean_mb()

        assert mean == pytest.approx(150.0, rel=0.01)

    def test_get_mean_mb_empty(self):
        """Test getting mean with no samples."""
        tracker = MemoryTracker()

        mean = tracker.get_mean_mb()

        assert mean == 0.0

    def test_get_samples(self):
        """Test getting all samples."""
        tracker = MemoryTracker()

        tracker.samples = [100.0, 150.0, 200.0]

        samples = tracker.get_samples()

        assert samples == [100.0, 150.0, 200.0]
        # Should return a copy
        samples.append(250.0)
        assert len(tracker.samples) == 3

    def test_reset(self):
        """Test resetting samples."""
        tracker = MemoryTracker()

        tracker.sample()
        tracker.sample()

        assert len(tracker.samples) > 0

        tracker.reset()

        assert len(tracker.samples) == 0

    def test_track_context_manager(self):
        """Test track context manager."""
        tracker = MemoryTracker()

        with tracker.track(sample_interval_ms=50):
            # Allocate some memory
            np.zeros((1000, 1000))
            time.sleep(0.2)  # Allow time for sampling

        # Should have collected some samples
        assert len(tracker.samples) > 0
        assert tracker.get_peak_mb() > 0


class TestAccuracyMeasurement:
    """Test suite for AccuracyMeasurement."""

    def test_calculate_fpr_perfect(self):
        """Test FPR calculation with perfect predictions."""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 1, 1, 1])

        fpr = AccuracyMeasurement.calculate_fpr(y_true, y_pred)

        assert fpr == 0.0

    def test_calculate_fpr_with_false_positives(self):
        """Test FPR calculation with false positives."""
        # True: [Normal, Normal, Normal, Normal, Attack, Attack]
        # Pred: [Normal, Attack, Attack, Normal, Attack, Attack]
        # FP = 2 (predicted attack but actually normal)
        # TN = 2 (predicted normal and actually normal)
        # FPR = 2 / (2 + 2) = 0.5
        y_true = np.array([0, 0, 0, 0, 1, 1])
        y_pred = np.array([0, 1, 1, 0, 1, 1])

        fpr = AccuracyMeasurement.calculate_fpr(y_true, y_pred)

        assert fpr == pytest.approx(0.5, rel=0.01)

    def test_calculate_fpr_all_attacks(self):
        """Test FPR calculation when all samples are attacks."""
        y_true = np.array([1, 1, 1, 2, 2, 2])
        y_pred = np.array([1, 1, 1, 2, 2, 2])

        fpr = AccuracyMeasurement.calculate_fpr(y_true, y_pred)

        # No normal samples, so FPR should be 0
        assert fpr == 0.0

    def test_calculate_fpr_all_normal(self):
        """Test FPR calculation when all samples are normal."""
        y_true = np.array([0, 0, 0, 0, 0])
        y_pred = np.array([0, 0, 1, 1, 0])

        # FP = 2, TN = 3, FPR = 2/5 = 0.4
        fpr = AccuracyMeasurement.calculate_fpr(y_true, y_pred)

        assert fpr == pytest.approx(0.4, rel=0.01)

    def test_calculate_metrics(self):
        """Test calculating comprehensive metrics."""
        y_true = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2])
        y_pred = np.array([0, 0, 1, 1, 1, 0, 2, 2, 2])

        metrics = AccuracyMeasurement.calculate_metrics(y_true, y_pred)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "fpr" in metrics

        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1
        assert 0 <= metrics["fpr"] <= 1

    def test_calculate_metrics_perfect(self):
        """Test metrics with perfect predictions."""
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 0, 1, 1, 2, 2])

        metrics = AccuracyMeasurement.calculate_metrics(y_true, y_pred)

        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1_score"] == 1.0
        assert metrics["fpr"] == 0.0
