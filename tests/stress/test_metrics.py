"""Unit tests for PerformanceMetrics data model."""

import pytest

from tests.stress.metrics import PerformanceMetrics


class TestPerformanceMetrics:
    """Test suite for PerformanceMetrics class."""

    def test_initialization(self):
        """Test PerformanceMetrics initialization with default values."""
        metrics = PerformanceMetrics()

        assert metrics.latencies == []
        assert metrics.latency_p50 == 0.0
        assert metrics.latency_p95 == 0.0
        assert metrics.latency_p99 == 0.0
        assert metrics.throughput_fps == 0.0
        assert metrics.total_flows == 0
        assert metrics.fpr == 0.0
        assert metrics.memory_samples == []
        assert metrics.attack_counts == {}
        assert metrics.timestamp is not None

    def test_add_latency(self):
        """Test adding latency measurements."""
        metrics = PerformanceMetrics()

        metrics.add_latency(10.5)
        metrics.add_latency(20.3)
        metrics.add_latency(15.7)

        assert len(metrics.latencies) == 3
        assert metrics.latencies == [10.5, 20.3, 15.7]

    def test_add_latency_negative_ignored(self):
        """Test that negative latency values are ignored."""
        metrics = PerformanceMetrics()

        metrics.add_latency(10.0)
        metrics.add_latency(-5.0)  # Should be ignored
        metrics.add_latency(20.0)

        assert len(metrics.latencies) == 2
        assert metrics.latencies == [10.0, 20.0]

    def test_add_memory_sample(self):
        """Test adding memory samples."""
        metrics = PerformanceMetrics()

        metrics.add_memory_sample(100.5)
        metrics.add_memory_sample(150.3)
        metrics.add_memory_sample(120.7)

        assert len(metrics.memory_samples) == 3
        assert metrics.memory_samples == [100.5, 150.3, 120.7]

    def test_add_memory_sample_negative_ignored(self):
        """Test that negative memory values are ignored."""
        metrics = PerformanceMetrics()

        metrics.add_memory_sample(100.0)
        metrics.add_memory_sample(-50.0)  # Should be ignored
        metrics.add_memory_sample(200.0)

        assert len(metrics.memory_samples) == 2
        assert metrics.memory_samples == [100.0, 200.0]

    def test_calculate_statistics_latency(self):
        """Test latency statistics calculation."""
        metrics = PerformanceMetrics()

        # Add latency measurements
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for lat in latencies:
            metrics.add_latency(lat)

        metrics.calculate_statistics()

        assert metrics.latency_p50 == pytest.approx(55.0, rel=0.1)
        assert metrics.latency_p95 == pytest.approx(95.5, rel=0.1)
        assert metrics.latency_p99 == pytest.approx(99.1, rel=0.1)
        assert metrics.latency_mean == pytest.approx(55.0, rel=0.1)
        assert metrics.latency_std > 0

    def test_calculate_statistics_memory(self):
        """Test memory statistics calculation."""
        metrics = PerformanceMetrics()

        # Add memory samples
        memory_samples = [100.0, 150.0, 200.0, 250.0, 300.0]
        for mem in memory_samples:
            metrics.add_memory_sample(mem)

        metrics.calculate_statistics()

        assert metrics.memory_peak == 300.0
        assert metrics.memory_mean == pytest.approx(200.0, rel=0.01)

    def test_calculate_statistics_throughput(self):
        """Test throughput calculation."""
        metrics = PerformanceMetrics()

        metrics.total_flows = 100000
        metrics.duration_seconds = 10.0

        metrics.calculate_statistics()

        assert metrics.throughput_fps == pytest.approx(10000.0, rel=0.01)

    def test_calculate_statistics_empty_latencies(self):
        """Test statistics calculation with no latency data."""
        metrics = PerformanceMetrics()

        metrics.calculate_statistics()

        assert metrics.latency_p50 == 0.0
        assert metrics.latency_p95 == 0.0
        assert metrics.latency_p99 == 0.0
        assert metrics.latency_mean == 0.0

    def test_get_percentile(self):
        """Test getting specific percentiles."""
        metrics = PerformanceMetrics()

        latencies = list(range(1, 101))  # 1 to 100
        for lat in latencies:
            metrics.add_latency(float(lat))

        p50 = metrics.get_percentile(50)
        p95 = metrics.get_percentile(95)

        assert p50 == pytest.approx(50.5, rel=0.1)
        assert p95 == pytest.approx(95.05, rel=0.1)

    def test_get_percentile_empty(self):
        """Test getting percentile with no data."""
        metrics = PerformanceMetrics()

        assert metrics.get_percentile(50) == 0.0
        assert metrics.get_percentile(95) == 0.0

    def test_get_summary(self):
        """Test getting summary dictionary."""
        metrics = PerformanceMetrics()

        # Add some data
        metrics.add_latency(10.0)
        metrics.add_latency(20.0)
        metrics.add_memory_sample(100.0)
        metrics.total_flows = 1000
        metrics.duration_seconds = 10.0
        metrics.fpr = 0.015
        metrics.accuracy = 0.98
        metrics.attack_counts = {"DoS": 50, "Normal": 950}

        metrics.calculate_statistics()

        summary = metrics.get_summary()

        assert "timestamp" in summary
        assert "latency" in summary
        assert "throughput" in summary
        assert "accuracy" in summary
        assert "memory" in summary
        assert "attack_distribution" in summary

        assert summary["latency"]["samples"] == 2
        assert summary["throughput"]["total_flows"] == 1000
        assert summary["accuracy"]["fpr"] == 0.015
        assert summary["memory"]["peak_mb"] == 100.0
        assert summary["attack_distribution"]["DoS"] == 50

    def test_meets_targets_all_pass(self):
        """Test meets_targets when all targets are met."""
        metrics = PerformanceMetrics()

        metrics.latency_p95 = 45.0  # < 50ms
        metrics.fpr = 0.015  # < 2%
        metrics.throughput_fps = 150000  # >= 100000

        assert metrics.meets_targets() is True

    def test_meets_targets_latency_fail(self):
        """Test meets_targets when latency target is not met."""
        metrics = PerformanceMetrics()

        metrics.latency_p95 = 55.0  # > 50ms (FAIL)
        metrics.fpr = 0.015  # < 2%
        metrics.throughput_fps = 150000  # >= 100000

        assert metrics.meets_targets() is False

    def test_meets_targets_fpr_fail(self):
        """Test meets_targets when FPR target is not met."""
        metrics = PerformanceMetrics()

        metrics.latency_p95 = 45.0  # < 50ms
        metrics.fpr = 0.025  # > 2% (FAIL)
        metrics.throughput_fps = 150000  # >= 100000

        assert metrics.meets_targets() is False

    def test_meets_targets_throughput_fail(self):
        """Test meets_targets when throughput target is not met."""
        metrics = PerformanceMetrics()

        metrics.latency_p95 = 45.0  # < 50ms
        metrics.fpr = 0.015  # < 2%
        metrics.throughput_fps = 50000  # < 100000 (FAIL)

        assert metrics.meets_targets() is False

    def test_repr(self):
        """Test string representation."""
        metrics = PerformanceMetrics()

        metrics.latency_p95 = 45.5
        metrics.fpr = 0.015
        metrics.throughput_fps = 150000
        metrics.total_flows = 1000000

        repr_str = repr(metrics)

        assert "45.50ms" in repr_str
        assert "0.0150" in repr_str
        assert "150000" in repr_str
        assert "1000000" in repr_str
