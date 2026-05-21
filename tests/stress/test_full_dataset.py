"""Full-dataset stress runner for CICIDS2017 or synthetic NIDS CSV files."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from src.nids.data.loader import engineer_features, get_label_mapping, map_labels
from src.nids.models.classifier import NIDSClassifier
from src.nids.reporting.performance import PerformanceReport, ReportGenerator
from tests.stress.batch_processor import BatchProcessor
from tests.stress.measurement import MemoryTracker


class StressTestRunner:
    """Run large-dataset inference tests and generate production metrics."""

    def __init__(
        self,
        classifier: NIDSClassifier,
        dataset_path: str,
        batch_size: int = 10000,
        output_dir: str = "reports",
        measure_per_flow_latency: bool = True,
    ):
        self.classifier = classifier
        self.dataset_path = Path(dataset_path)
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.measure_per_flow_latency = measure_per_flow_latency
        self.batch_processor = BatchProcessor(batch_size=batch_size)
        self.memory_tracker = MemoryTracker()
        self.label_mapping = get_label_mapping()

    @staticmethod
    def calculate_fpr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate false positive rate where class 0 is Normal."""
        fp = np.sum((y_pred != 0) & (y_true == 0))
        tn = np.sum((y_pred == 0) & (y_true == 0))
        denominator = fp + tn
        return float(fp / denominator) if denominator else 0.0

    def run_full_test(self, max_rows: Optional[int] = None) -> PerformanceReport:
        if self.classifier.model is None:
            raise RuntimeError("Classifier model must be loaded before stress testing")
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")

        latencies: List[float] = []
        throughput_samples: List[float] = []
        y_true_all: List[int] = []
        y_pred_all: List[int] = []
        attack_distribution: Dict[str, int] = {}
        total_rows = 0
        started = time.perf_counter()

        for chunk in self.batch_processor.read_csv_batches(str(self.dataset_path)):
            if max_rows is not None:
                remaining = max_rows - total_rows
                if remaining <= 0:
                    break
                chunk = chunk.head(remaining)

            X = engineer_features(chunk).values
            y_true = self._labels_from_chunk(chunk)

            batch_started = time.perf_counter()
            y_pred, _ = self.classifier.predict(X)
            batch_seconds = time.perf_counter() - batch_started
            if batch_seconds > 0:
                throughput_samples.append(len(X) / batch_seconds)

            if self.measure_per_flow_latency:
                latencies.extend(self.measure_latency(X))
            else:
                per_flow_ms = (batch_seconds * 1000) / max(len(X), 1)
                latencies.extend([per_flow_ms] * len(X))

            if y_true is not None:
                y_true_all.extend(y_true.tolist())
                y_pred_all.extend(y_pred.astype(int).tolist())

            for pred in y_pred:
                label = self.classifier.reverse_mapping.get(int(pred), str(pred))
                attack_distribution[label] = attack_distribution.get(label, 0) + 1

            self.memory_tracker.sample()
            total_rows += len(X)

        duration = time.perf_counter() - started
        latency_metrics = self._latency_metrics(latencies)
        accuracy_metrics = self._accuracy_metrics(y_true_all, y_pred_all)
        fpr = (
            self.calculate_fpr(np.array(y_true_all), np.array(y_pred_all))
            if y_true_all
            else 0.0
        )

        report = PerformanceReport(
            dataset_info={
                "path": str(self.dataset_path),
                "rows_processed": total_rows,
                "duration_seconds": duration,
                "batch_size": self.batch_size,
                "measured_per_flow_latency": self.measure_per_flow_latency,
            },
            latency_metrics=latency_metrics,
            throughput_fps=float(np.mean(throughput_samples)) if throughput_samples else 0.0,
            fpr=fpr,
            accuracy_metrics=accuracy_metrics,
            memory_metrics={
                "peak_mb": self.memory_tracker.get_peak_mb(),
                "mean_mb": self.memory_tracker.get_mean_mb(),
            },
            attack_distribution=attack_distribution,
        )
        return report

    def measure_latency(self, X: np.ndarray) -> List[float]:
        """Measure single-flow inference latency for every row in X."""
        latencies = []
        for row in X:
            started = time.perf_counter()
            self.classifier.predict_single(row)
            latencies.append((time.perf_counter() - started) * 1000)
        return latencies

    def measure_throughput(self, X: np.ndarray) -> float:
        started = time.perf_counter()
        self.classifier.predict(X)
        duration = time.perf_counter() - started
        return len(X) / duration if duration > 0 else 0.0

    def generate_report(self, report: PerformanceReport, output_format: str = "markdown") -> Path:
        suffix = "md" if output_format in {"markdown", "md"} else output_format
        path = ReportGenerator.timestamped_path(str(self.output_dir), suffix=suffix)
        return ReportGenerator(report).save_report(str(path), output_format=output_format)

    def _labels_from_chunk(self, chunk: pd.DataFrame) -> Optional[np.ndarray]:
        if "Label" not in chunk.columns:
            return None
        return np.array(
            [
                self.label_mapping.get(map_labels(str(label)), 0)
                for label in chunk["Label"].values
            ],
            dtype=int,
        )

    def _latency_metrics(self, latencies: List[float]) -> Dict[str, float]:
        if not latencies:
            return {
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "mean_ms": 0.0,
                "max_ms": 0.0,
            }
        values = np.array(latencies)
        return {
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "p99_ms": float(np.percentile(values, 99)),
            "mean_ms": float(np.mean(values)),
            "max_ms": float(np.max(values)),
        }

    def _accuracy_metrics(self, y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
        if not y_true:
            return {
                "accuracy": 0.0,
                "precision_macro": 0.0,
                "recall_macro": 0.0,
                "f1_macro": 0.0,
            }

        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision_macro": float(
                precision_score(y_true, y_pred, average="macro", zero_division=0)
            ),
            "recall_macro": float(
                recall_score(y_true, y_pred, average="macro", zero_division=0)
            ),
            "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        }


@pytest.mark.skipif(
    not Path("models/nids_model.pkl").exists() or not Path("data/nids_synthetic.csv").exists(),
    reason="Trained model and synthetic data are required for stress smoke test",
)
def test_stress_runner_smoke_on_synthetic_subset(tmp_path):
    classifier = NIDSClassifier()
    classifier.load("models/nids_model.pkl")

    runner = StressTestRunner(
        classifier=classifier,
        dataset_path="data/nids_synthetic.csv",
        batch_size=500,
        output_dir=str(tmp_path),
        measure_per_flow_latency=False,
    )
    report = runner.run_full_test(max_rows=1000)

    assert report.dataset_info["rows_processed"] == 1000
    assert report.latency_metrics["p95_ms"] >= 0
    assert report.throughput_fps > 0
    assert 0.0 <= report.fpr <= 1.0
    assert Path(runner.generate_report(report)).exists()
