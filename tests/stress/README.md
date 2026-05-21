# Stress Testing Infrastructure

This directory contains the stress testing infrastructure for validating NIDS performance on large datasets.

## Overview

The stress testing infrastructure provides:

1. **Performance Metrics Collection** - Comprehensive metrics tracking for latency, throughput, accuracy, and memory
2. **Batch Processing** - Memory-efficient processing of large datasets with automatic batch size adjustment
3. **Measurement Utilities** - Tools for measuring latency, throughput, memory usage, and accuracy

## Components

### PerformanceMetrics (`metrics.py`)

Data model for collecting and aggregating performance metrics during stress testing.

**Features:**
- Latency tracking (p50, p95, p99, mean, std)
- Throughput measurement (flows per second)
- Accuracy metrics (FPR, accuracy, precision, recall, F1)
- Memory usage tracking (peak, mean)
- Attack distribution tracking
- Production target validation

**Usage:**
```python
from tests.stress.metrics import PerformanceMetrics

metrics = PerformanceMetrics()

# Add measurements
metrics.add_latency(15.5)  # milliseconds
metrics.add_memory_sample(250.0)  # MB
metrics.total_flows = 100000
metrics.duration_seconds = 10.0

# Calculate statistics
metrics.calculate_statistics()

# Check if targets are met
if metrics.meets_targets():
    print("All production targets met!")

# Get summary
summary = metrics.get_summary()
```

### BatchProcessor (`batch_processor.py`)

Handles large dataset processing in batches to prevent out-of-memory errors.

**Features:**
- CSV file reading in chunks
- Batch processing with memory monitoring
- Automatic batch size adjustment on memory pressure
- Processing statistics tracking

**Usage:**
```python
from tests.stress.batch_processor import BatchProcessor

processor = BatchProcessor(
    batch_size=10000,
    memory_threshold_percent=80.0,
    auto_adjust_batch_size=True
)

# Read CSV in batches
for chunk in processor.read_csv_batches("large_dataset.csv"):
    # Process chunk
    process_data(chunk)

# Process numpy array in batches
def inference_fn(batch):
    return model.predict(batch)

results = list(processor.process_batches(X, inference_fn))

# Get statistics
stats = processor.get_stats()
print(f"Processed {stats['total_rows_processed']} rows in {stats['total_batches_processed']} batches")
```

### Measurement Utilities (`measurement.py`)

Utilities for measuring latency, throughput, memory, and accuracy.

**LatencyMeasurement:**
```python
from tests.stress.measurement import LatencyMeasurement

# Measure single function call
result, latency_ms = LatencyMeasurement.measure_single(model.predict, X)

# Measure batch processing
latencies = LatencyMeasurement.measure_batch(model.predict, X, batch_size=100)

# Use timer context manager
with LatencyMeasurement.timer("inference") as t:
    model.predict(X)
print(f"Took {t['elapsed_ms']:.2f}ms")
```

**ThroughputMeasurement:**
```python
from tests.stress.measurement import ThroughputMeasurement

# Measure throughput
throughput = ThroughputMeasurement.measure(model.predict, X, warmup_runs=3)
print(f"Throughput: {throughput:.0f} flows/sec")

# Calculate from duration
throughput = ThroughputMeasurement.measure_with_duration(
    total_items=100000,
    duration_seconds=10.0
)
```

**MemoryTracker:**
```python
from tests.stress.measurement import MemoryTracker

tracker = MemoryTracker()

# Track memory during operation
with tracker.track(sample_interval_ms=100):
    process_large_dataset()

print(f"Peak memory: {tracker.get_peak_mb():.2f}MB")
print(f"Mean memory: {tracker.get_mean_mb():.2f}MB")
```

**AccuracyMeasurement:**
```python
from tests.stress.measurement import AccuracyMeasurement

# Calculate FPR
fpr = AccuracyMeasurement.calculate_fpr(y_true, y_pred)

# Calculate all metrics
metrics = AccuracyMeasurement.calculate_metrics(y_true, y_pred)
print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"FPR: {metrics['fpr']:.4f}")
```

## Production Targets

The stress testing infrastructure validates against these production targets:

- **p95 Latency**: < 50ms
- **False Positive Rate (FPR)**: < 2%
- **Throughput**: >= 100,000 flows/sec (batch mode)

## Testing

Run the stress testing infrastructure tests:

```bash
# Run all stress tests
pytest tests/stress/ -v

# Run specific test file
pytest tests/stress/test_metrics.py -v

# Run with coverage
pytest tests/stress/ --cov=tests.stress --cov-report=html
```

## Directory Structure

```
tests/stress/
├── __init__.py              # Package initialization
├── README.md                # This file
├── metrics.py               # PerformanceMetrics data model
├── batch_processor.py       # Batch processing utilities
├── measurement.py           # Measurement utilities
├── conftest.py              # Pytest fixtures
├── test_metrics.py          # Tests for PerformanceMetrics
├── test_batch_processor.py  # Tests for BatchProcessor
└── test_measurement.py      # Tests for measurement utilities
```

## Next Steps

This infrastructure will be used by:

1. **Full Dataset Stress Tests** (Task 2) - Test on complete CICIDS2017 dataset
2. **Performance Benchmarking** (Task 6) - Automated performance benchmarking
3. **Integration Tests** (Task 4) - End-to-end pipeline validation

## Requirements Validated

This infrastructure supports the following requirements:

- **Requirement 1.1**: Measure inference latency for all flows
- **Requirement 1.2**: Calculate False Positive Rate
- **Requirement 1.3**: Validate p95 latency < 50ms
- **Requirement 1.4**: Validate FPR < 2%
- **Requirement 1.5**: Process >= 100,000 flows/sec
- **Requirement 1.6**: Generate performance reports
- **Requirement 1.7**: Include latency distribution, throughput, FPR, accuracy
- **Requirement 1.8**: Process data in batches to prevent OOM errors
