"""Unit tests for BatchProcessor."""

import numpy as np
import pandas as pd
import pytest

from tests.stress.batch_processor import BatchProcessor


class TestBatchProcessor:
    """Test suite for BatchProcessor class."""

    def test_initialization(self):
        """Test BatchProcessor initialization."""
        processor = BatchProcessor(batch_size=5000, memory_threshold_percent=75.0)

        assert processor.batch_size == 5000
        assert processor.initial_batch_size == 5000
        assert processor.memory_threshold_percent == 75.0
        assert processor.auto_adjust_batch_size is True
        assert processor.total_batches_processed == 0
        assert processor.total_rows_processed == 0

    def test_get_memory_usage_percent(self):
        """Test getting memory usage percentage."""
        processor = BatchProcessor()

        usage = processor.get_memory_usage_percent()

        assert isinstance(usage, float)
        assert 0 <= usage <= 100

    def test_get_available_memory_mb(self):
        """Test getting available memory."""
        processor = BatchProcessor()

        available = processor.get_available_memory_mb()

        assert isinstance(available, float)
        assert available > 0

    def test_check_memory_pressure_no_pressure(self):
        """Test memory pressure check when usage is low."""
        processor = BatchProcessor(memory_threshold_percent=99.0)

        # With 99% threshold, should not detect pressure
        has_pressure = processor.check_memory_pressure()

        # This might be True or False depending on system state
        assert isinstance(has_pressure, bool)

    def test_read_csv_batches(self, temp_csv_file):
        """Test reading CSV file in batches."""
        processor = BatchProcessor(batch_size=100)

        batches = list(processor.read_csv_batches(temp_csv_file))

        assert len(batches) > 0
        assert all(isinstance(batch, pd.DataFrame) for batch in batches)
        assert processor.total_batches_processed > 0
        assert processor.total_rows_processed == 1000  # From fixture

    def test_read_csv_batches_file_not_found(self):
        """Test reading non-existent CSV file."""
        processor = BatchProcessor()

        with pytest.raises(FileNotFoundError):
            list(processor.read_csv_batches("nonexistent.csv"))

    def test_read_csv_batches_empty_file(self, tmp_path):
        """Test reading empty CSV file."""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")

        processor = BatchProcessor()

        with pytest.raises(ValueError, match="empty"):
            list(processor.read_csv_batches(str(empty_file)))

    def test_read_csv_batches_custom_chunksize(self, temp_csv_file):
        """Test reading CSV with custom chunk size."""
        processor = BatchProcessor(batch_size=100)

        batches = list(processor.read_csv_batches(temp_csv_file, chunksize=50))

        # Should have more batches with smaller chunk size
        assert len(batches) >= 20  # 1000 rows / 50 = 20 batches

    def test_process_batches(self):
        """Test processing numpy array in batches."""
        processor = BatchProcessor(batch_size=100)

        data = np.arange(1000)
        results = []

        def process_fn(batch):
            return np.sum(batch)

        for result in processor.process_batches(data, process_fn):
            results.append(result)

        assert len(results) == 10  # 1000 / 100 = 10 batches
        assert processor.total_batches_processed == 10
        assert processor.total_rows_processed == 1000

    def test_process_batches_custom_size(self):
        """Test processing with custom batch size."""
        processor = BatchProcessor(batch_size=100)

        data = np.arange(1000)
        results = []

        def process_fn(batch):
            return len(batch)

        for result in processor.process_batches(data, process_fn, batch_size=250):
            results.append(result)

        assert len(results) == 4  # 1000 / 250 = 4 batches
        assert results == [250, 250, 250, 250]

    def test_process_batches_uneven_division(self):
        """Test processing when data doesn't divide evenly."""
        processor = BatchProcessor(batch_size=300)

        data = np.arange(1000)
        results = []

        def process_fn(batch):
            return len(batch)

        for result in processor.process_batches(data, process_fn):
            results.append(result)

        assert len(results) == 4  # 1000 / 300 = 3.33, so 4 batches
        assert results == [300, 300, 300, 100]  # Last batch is smaller

    def test_process_dataframe_batches(self, sample_dataframe):
        """Test processing DataFrame in batches."""
        processor = BatchProcessor(batch_size=200)

        results = []

        def process_fn(batch):
            return len(batch)

        for result in processor.process_dataframe_batches(sample_dataframe, process_fn):
            results.append(result)

        assert len(results) == 5  # 1000 / 200 = 5 batches
        assert sum(results) == 1000
        assert processor.total_rows_processed == 1000

    def test_process_dataframe_batches_custom_size(self, sample_dataframe):
        """Test processing DataFrame with custom batch size."""
        processor = BatchProcessor(batch_size=100)

        results = []

        def process_fn(batch):
            return batch.shape[0]

        for result in processor.process_dataframe_batches(
            sample_dataframe, process_fn, batch_size=333
        ):
            results.append(result)

        assert len(results) == 4  # 1000 / 333 = 3.003, so 4 batches

    def test_get_stats(self):
        """Test getting processing statistics."""
        processor = BatchProcessor(batch_size=100, auto_adjust_batch_size=False)

        data = np.arange(500)

        def process_fn(batch):
            return len(batch)

        list(processor.process_batches(data, process_fn))

        stats = processor.get_stats()

        assert stats["total_batches_processed"] == 5
        assert stats["total_rows_processed"] == 500
        assert stats["current_batch_size"] == 100
        assert stats["initial_batch_size"] == 100
        assert "memory_usage_percent" in stats
        assert "available_memory_mb" in stats

    def test_reset_stats(self):
        """Test resetting processing statistics."""
        processor = BatchProcessor(batch_size=100)

        data = np.arange(500)

        def process_fn(batch):
            return len(batch)

        list(processor.process_batches(data, process_fn))

        assert processor.total_batches_processed > 0
        assert processor.total_rows_processed > 0

        processor.reset_stats()

        assert processor.total_batches_processed == 0
        assert processor.total_rows_processed == 0
        assert processor.batch_size == processor.initial_batch_size

    def test_adjust_batch_size_disabled(self):
        """Test that batch size adjustment can be disabled."""
        processor = BatchProcessor(
            batch_size=10000,
            auto_adjust_batch_size=False
        )

        initial_size = processor.batch_size
        processor.adjust_batch_size()

        # Batch size should not change when auto-adjust is disabled
        assert processor.batch_size == initial_size

    def test_process_batches_error_handling(self):
        """Test error handling during batch processing."""
        processor = BatchProcessor(batch_size=100)

        data = np.arange(500)

        def failing_process_fn(batch):
            if len(batch) > 50:
                raise ValueError("Batch too large")
            return len(batch)

        with pytest.raises(ValueError, match="Batch too large"):
            list(processor.process_batches(data, failing_process_fn))
