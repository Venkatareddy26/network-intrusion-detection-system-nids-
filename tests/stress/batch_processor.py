"""Batch processing utilities for handling large datasets without OOM errors."""

from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import numpy as np
import pandas as pd
import psutil

from src.nids.utils.logging import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Handles large dataset processing in batches to prevent out-of-memory errors.

    This class provides utilities for:
    - Reading large CSV files in chunks
    - Processing data in batches with memory monitoring
    - Automatic batch size adjustment based on available memory
    """

    def __init__(
        self,
        batch_size: int = 10000,
        memory_threshold_percent: float = 80.0,
        auto_adjust_batch_size: bool = True
    ):
        """Initialize batch processor.

        Args:
            batch_size: Number of rows to process per batch
            memory_threshold_percent: Memory usage threshold for warnings (0-100)
            auto_adjust_batch_size: Whether to automatically reduce batch size on memory pressure
        """
        self.batch_size = batch_size
        self.initial_batch_size = batch_size
        self.memory_threshold_percent = memory_threshold_percent
        self.auto_adjust_batch_size = auto_adjust_batch_size
        self.total_batches_processed = 0
        self.total_rows_processed = 0

    def get_memory_usage_percent(self) -> float:
        """Get current memory usage percentage.

        Returns:
            Memory usage as percentage (0-100)
        """
        return psutil.virtual_memory().percent

    def get_available_memory_mb(self) -> float:
        """Get available memory in megabytes.

        Returns:
            Available memory in MB
        """
        return psutil.virtual_memory().available / (1024 * 1024)

    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure.

        Returns:
            True if memory usage exceeds threshold, False otherwise
        """
        current_usage = self.get_memory_usage_percent()
        if current_usage >= self.memory_threshold_percent:
            logger.warning(
                f"Memory pressure detected: {current_usage:.1f}% used "
                f"(threshold: {self.memory_threshold_percent:.1f}%)"
            )
            return True
        return False

    def adjust_batch_size(self) -> None:
        """Automatically reduce batch size if under memory pressure."""
        if not self.auto_adjust_batch_size:
            return

        if self.check_memory_pressure():
            old_size = self.batch_size
            self.batch_size = max(1000, self.batch_size // 2)
            logger.warning(
                f"Reducing batch size from {old_size} to {self.batch_size} "
                f"due to memory pressure"
            )

    def read_csv_batches(
        self,
        filepath: str,
        chunksize: Optional[int] = None
    ) -> Iterator[pd.DataFrame]:
        """Read CSV file in batches.

        Args:
            filepath: Path to CSV file
            chunksize: Number of rows per chunk (uses batch_size if None)

        Yields:
            DataFrame chunks

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty or invalid
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {filepath}")

        chunk_size = chunksize or self.batch_size
        logger.info(f"Reading CSV in batches of {chunk_size} rows from {filepath}")

        try:
            for chunk_num, chunk in enumerate(
                pd.read_csv(filepath, chunksize=chunk_size, low_memory=False),
                start=1
            ):
                # Check memory before processing each chunk
                self.adjust_batch_size()

                logger.debug(
                    f"Processing chunk {chunk_num}: {len(chunk)} rows, "
                    f"memory: {self.get_memory_usage_percent():.1f}%"
                )

                self.total_batches_processed += 1
                self.total_rows_processed += len(chunk)

                yield chunk

        except pd.errors.EmptyDataError:
            raise ValueError(f"CSV file is empty or invalid: {filepath}")
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}", exc_info=True)
            raise

    def process_batches(
        self,
        data: np.ndarray,
        process_fn: Callable[[np.ndarray], Any],
        batch_size: Optional[int] = None
    ) -> Iterator[Any]:
        """Process numpy array in batches.

        Args:
            data: Input data array
            process_fn: Function to apply to each batch
            batch_size: Batch size (uses self.batch_size if None)

        Yields:
            Results from process_fn for each batch
        """
        batch_sz = batch_size or self.batch_size
        total_samples = len(data)

        logger.info(
            f"Processing {total_samples} samples in batches of {batch_sz}"
        )

        for start_idx in range(0, total_samples, batch_sz):
            # Check memory before processing each batch
            self.adjust_batch_size()

            end_idx = min(start_idx + batch_sz, total_samples)
            batch = data[start_idx:end_idx]

            logger.debug(
                f"Processing batch [{start_idx}:{end_idx}], "
                f"memory: {self.get_memory_usage_percent():.1f}%"
            )

            try:
                result = process_fn(batch)
                self.total_batches_processed += 1
                self.total_rows_processed += len(batch)
                yield result
            except Exception as e:
                logger.error(
                    f"Error processing batch [{start_idx}:{end_idx}]: {e}",
                    exc_info=True
                )
                raise

    def process_dataframe_batches(
        self,
        df: pd.DataFrame,
        process_fn: Callable[[pd.DataFrame], Any],
        batch_size: Optional[int] = None
    ) -> Iterator[Any]:
        """Process DataFrame in batches.

        Args:
            df: Input DataFrame
            process_fn: Function to apply to each batch
            batch_size: Batch size (uses self.batch_size if None)

        Yields:
            Results from process_fn for each batch
        """
        batch_sz = batch_size or self.batch_size
        total_rows = len(df)

        logger.info(
            f"Processing DataFrame with {total_rows} rows in batches of {batch_sz}"
        )

        for start_idx in range(0, total_rows, batch_sz):
            # Check memory before processing each batch
            self.adjust_batch_size()

            end_idx = min(start_idx + batch_sz, total_rows)
            batch = df.iloc[start_idx:end_idx]

            logger.debug(
                f"Processing batch [{start_idx}:{end_idx}], "
                f"memory: {self.get_memory_usage_percent():.1f}%"
            )

            try:
                result = process_fn(batch)
                self.total_batches_processed += 1
                self.total_rows_processed += len(batch)
                yield result
            except Exception as e:
                logger.error(
                    f"Error processing batch [{start_idx}:{end_idx}]: {e}",
                    exc_info=True
                )
                raise

    def get_stats(self) -> dict:
        """Get processing statistics.

        Returns:
            Dictionary with processing stats
        """
        return {
            "total_batches_processed": self.total_batches_processed,
            "total_rows_processed": self.total_rows_processed,
            "current_batch_size": self.batch_size,
            "initial_batch_size": self.initial_batch_size,
            "memory_usage_percent": self.get_memory_usage_percent(),
            "available_memory_mb": self.get_available_memory_mb(),
        }

    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.total_batches_processed = 0
        self.total_rows_processed = 0
        self.batch_size = self.initial_batch_size
        logger.info("Batch processor statistics reset")
