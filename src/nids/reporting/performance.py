"""Performance report generation for NIDS stress tests and benchmarks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_TARGETS = {
    "p95_latency_ms": 50.0,
    "fpr": 0.02,
    "throughput_fps": 100000.0,
    "f1_macro": 0.97,
}


@dataclass
class PerformanceReport:
    """Serializable performance report."""

    dataset_info: Dict[str, Any]
    latency_metrics: Dict[str, float]
    throughput_fps: float
    fpr: float
    accuracy_metrics: Dict[str, float]
    memory_metrics: Dict[str, float]
    attack_distribution: Dict[str, int] = field(default_factory=dict)
    targets: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TARGETS))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def target_status(self) -> Dict[str, bool]:
        """Return pass/fail status for production target metrics."""
        return {
            "p95_latency": self.latency_metrics.get("p95_ms", 0.0)
            < self.targets["p95_latency_ms"],
            "fpr": self.fpr < self.targets["fpr"],
            "throughput": self.throughput_fps >= self.targets["throughput_fps"],
            "f1_macro": self.accuracy_metrics.get("f1_macro", 0.0)
            >= self.targets["f1_macro"],
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["target_status"] = self.target_status()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_markdown(self) -> str:
        status = self.target_status()
        rows = [
            ("P50 latency", f"{self.latency_metrics.get('p50_ms', 0.0):.2f} ms", ""),
            (
                "P95 latency",
                f"{self.latency_metrics.get('p95_ms', 0.0):.2f} ms",
                "PASS" if status["p95_latency"] else "FAIL",
            ),
            ("P99 latency", f"{self.latency_metrics.get('p99_ms', 0.0):.2f} ms", ""),
            (
                "Throughput",
                f"{self.throughput_fps:,.0f} flows/sec",
                "PASS" if status["throughput"] else "FAIL",
            ),
            ("False Positive Rate", f"{self.fpr:.4%}", "PASS" if status["fpr"] else "FAIL"),
            (
                "Macro F1",
                f"{self.accuracy_metrics.get('f1_macro', 0.0):.4f}",
                "PASS" if status["f1_macro"] else "FAIL",
            ),
        ]
        metric_table = "\n".join(
            f"| {name} | {value} | {result} |" for name, value, result in rows
        )
        attack_rows = "\n".join(
            f"| {name} | {count} |" for name, count in self.attack_distribution.items()
        )
        if not attack_rows:
            attack_rows = "| None | 0 |"

        return f"""# NIDS Performance Report

Generated: {self.timestamp}

## Dataset

```json
{json.dumps(self.dataset_info, indent=2, default=str)}
```

## Metrics

| Metric | Value | Target |
|---|---:|:---:|
{metric_table}

## Accuracy

```json
{json.dumps(self.accuracy_metrics, indent=2, default=str)}
```

## Memory

```json
{json.dumps(self.memory_metrics, indent=2, default=str)}
```

## Attack Distribution

| Attack Type | Count |
|---|---:|
{attack_rows}
"""

    def to_html(self) -> str:
        markdown = self.to_markdown()
        escaped = (
            markdown.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<html><body><pre>{escaped}</pre></body></html>"


class ReportGenerator:
    """Creates and persists performance reports."""

    def __init__(self, report: PerformanceReport):
        self.report = report

    def generate_report(self, output_format: str = "markdown") -> str:
        if output_format == "json":
            return self.report.to_json()
        if output_format == "html":
            return self.report.to_html()
        if output_format in {"markdown", "md"}:
            return self.report.to_markdown()
        raise ValueError("output_format must be one of: markdown, json, html")

    def save_report(self, filepath: str, output_format: Optional[str] = None) -> Path:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        if output_format is None:
            suffix = path.suffix.lower().lstrip(".")
            output_format = "markdown" if suffix in {"md", "markdown"} else suffix
        path.write_text(self.generate_report(output_format), encoding="utf-8")
        return path

    @staticmethod
    def timestamped_path(directory: str, suffix: str = "md") -> Path:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        return Path(directory) / f"nids-performance-{timestamp}.{suffix}"


class ChartGenerator:
    """Creates Plotly charts for report artifacts."""

    def create_latency_distribution(self, latencies: List[float]):
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Histogram(x=latencies, nbinsx=50, name="Latency"))
        fig.add_vline(x=50.0, line_dash="dash", line_color="red")
        fig.update_layout(
            title="Inference Latency Distribution",
            xaxis_title="Latency (ms)",
            yaxis_title="Flow count",
        )
        return fig

    def create_throughput_chart(self, throughput_data: List[float]):
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=throughput_data, mode="lines", name="Throughput"))
        fig.add_hline(y=100000.0, line_dash="dash", line_color="red")
        fig.update_layout(
            title="Throughput Over Time",
            xaxis_title="Batch",
            yaxis_title="Flows/sec",
        )
        return fig

    def create_confusion_matrix(self, y_true, y_pred, labels: Optional[List[str]] = None):
        import numpy as np
        import plotly.graph_objects as go
        from sklearn.metrics import confusion_matrix

        matrix = confusion_matrix(y_true, y_pred)
        axis_labels = labels or [str(i) for i in range(matrix.shape[0])]
        fig = go.Figure(
            data=go.Heatmap(
                z=np.asarray(matrix),
                x=axis_labels,
                y=axis_labels,
                colorscale="Blues",
            )
        )
        fig.update_layout(
            title="Confusion Matrix",
            xaxis_title="Predicted",
            yaxis_title="Actual",
        )
        return fig
