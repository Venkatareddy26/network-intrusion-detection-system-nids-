"""Streaming simulation for real-time NIDS demos.

The simulator reads network-flow CSV files line by line, converts each row into
the existing NetworkFlow dataclass, and immediately pushes it through the
Pipeline. It also supports file-tail mode for demos where new rows are appended
to a log file.
"""

from __future__ import annotations

import csv
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from src.nids.data.loader import FEATURE_COLUMNS, engineer_features
from src.nids.pipeline.processor import Alert, NetworkFlow, Pipeline
from src.nids.utils.logging import get_logger

logger = get_logger(__name__)


def _first_present(row: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present value from a row using several possible keys."""
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        numeric = float(value)
        if np.isnan(numeric) or np.isinf(numeric):
            return default
        return numeric
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    return int(_coerce_float(value, float(default)))


def network_flow_from_row(row: Dict[str, Any]) -> NetworkFlow:
    """Create a NetworkFlow from CICIDS-style or normalized CSV row data."""
    features = engineer_features(pd.DataFrame([row])).iloc[0].to_dict()

    return NetworkFlow(
        timestamp=str(
            _first_present(row, "timestamp", "Timestamp", "time", default=datetime.now().isoformat())
        ),
        src_ip=str(
            _first_present(row, "src_ip", "Source IP", "SourceIP", "Src IP", default="0.0.0.0")
        ),
        dst_ip=str(
            _first_present(row, "dst_ip", "Destination IP", "DestinationIP", "Dst IP", default="0.0.0.0")
        ),
        src_port=_coerce_int(
            _first_present(row, "src_port", "Source Port", "Src Port", default=0)
        ),
        dst_port=_coerce_int(
            _first_present(row, "dst_port", "Destination Port", "Dst Port", default=0)
        ),
        protocol=str(_first_present(row, "protocol", "Protocol", default="TCP")),
        flow_duration=_coerce_float(features["flow_duration"]),
        total_fwd_packets=_coerce_int(features["total_fwd_packets"]),
        total_bwd_packets=_coerce_int(features["total_bwd_packets"]),
        total_length_fwd_packets=_coerce_float(features["total_length_fwd_packets"]),
        total_length_bwd_packets=_coerce_float(features["total_length_bwd_packets"]),
        fwd_packet_length_mean=_coerce_float(features["fwd_packet_length_mean"]),
        fwd_packet_length_std=_coerce_float(features["fwd_packet_length_std"]),
        bwd_packet_length_mean=_coerce_float(features["bwd_packet_length_mean"]),
        bwd_packet_length_std=_coerce_float(features["bwd_packet_length_std"]),
        flow_bytes_per_sec=_coerce_float(features["flow_bytes_per_sec"]),
        flow_packets_per_sec=_coerce_float(features["flow_packets_per_sec"]),
        flow_iat_mean=_coerce_float(features["flow_iat_mean"]),
        flow_iat_std=_coerce_float(features["flow_iat_std"]),
        flow_iat_max=_coerce_float(features["flow_iat_max"]),
        fwd_iat_total=_coerce_float(features["fwd_iat_total"]),
        fwd_iat_mean=_coerce_float(features["fwd_iat_mean"]),
        fwd_iat_std=_coerce_float(features["fwd_iat_std"]),
        bwd_iat_total=_coerce_float(features["bwd_iat_total"]),
        bwd_iat_mean=_coerce_float(features["bwd_iat_mean"]),
        bwd_iat_std=_coerce_float(features["bwd_iat_std"]),
        fwd_packets_per_sec=_coerce_float(features["fwd_packets_per_sec"]),
        bwd_packets_per_sec=_coerce_float(features["bwd_packets_per_sec"]),
        down_up_ratio=_coerce_float(features["down_up_ratio"]),
        avg_packet_size=_coerce_float(features["avg_packet_size"]),
        avg_fwd_segment_size=_coerce_float(features["avg_fwd_segment_size"]),
        avg_bwd_segment_size=_coerce_float(features["avg_bwd_segment_size"]),
        subflow_fwd_packets=_coerce_int(features["subflow_fwd_packets"]),
        subflow_bwd_packets=_coerce_int(features["subflow_bwd_packets"]),
        subflow_fwd_bytes=_coerce_float(features["subflow_fwd_bytes"]),
        subflow_bwd_bytes=_coerce_float(features["subflow_bwd_bytes"]),
    )


@dataclass
class StreamingStats:
    """Real-time streaming statistics."""

    target_fps: float
    total_flows_processed: int = 0
    alerts_generated: int = 0
    attack_distribution: Dict[str, int] = field(default_factory=dict)
    end_to_end_latencies: List[float] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)

    @property
    def elapsed_seconds(self) -> float:
        return max((datetime.utcnow() - self.start_time).total_seconds(), 0.0)

    @property
    def flows_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        return self.total_flows_processed / elapsed if elapsed > 0 else 0.0

    @property
    def alert_rate(self) -> float:
        elapsed = self.elapsed_seconds
        return self.alerts_generated / elapsed if elapsed > 0 else 0.0

    @property
    def avg_latency(self) -> float:
        if not self.end_to_end_latencies:
            return 0.0
        return float(np.mean(self.end_to_end_latencies))

    @property
    def p95_latency(self) -> float:
        if not self.end_to_end_latencies:
            return 0.0
        return float(np.percentile(np.array(self.end_to_end_latencies), 95))

    def record(self, latency_ms: float, alert: Optional[Alert]) -> None:
        self.total_flows_processed += 1
        self.end_to_end_latencies.append(latency_ms)
        if len(self.end_to_end_latencies) > 10000:
            self.end_to_end_latencies = self.end_to_end_latencies[-10000:]

        if alert is not None:
            self.alerts_generated += 1
            self.attack_distribution[alert.attack_type] = (
                self.attack_distribution.get(alert.attack_type, 0) + 1
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_flows_processed": self.total_flows_processed,
            "flows_per_second": self.flows_per_second,
            "target_fps": self.target_fps,
            "alerts_generated": self.alerts_generated,
            "alert_rate": self.alert_rate,
            "avg_latency_ms": self.avg_latency,
            "p95_latency_ms": self.p95_latency,
            "attack_distribution": dict(self.attack_distribution),
            "elapsed_seconds": self.elapsed_seconds,
        }


class FlowRateController:
    """Controls delay between flows to simulate a target flow rate."""

    def __init__(self, target_fps: float):
        self.set_rate(target_fps)
        self._next_emit_time = time.perf_counter()

    def set_rate(self, target_fps: float) -> None:
        if target_fps <= 0:
            raise ValueError("target_fps must be greater than zero")
        self.target_fps = float(target_fps)
        self.delay_seconds = 1.0 / self.target_fps

    def wait_for_next_flow(self) -> None:
        now = time.perf_counter()
        if self._next_emit_time > now:
            time.sleep(self._next_emit_time - now)
        self._next_emit_time = max(self._next_emit_time + self.delay_seconds, time.perf_counter())

    def adjust_rate(self, actual_fps: float) -> None:
        """Apply conservative adaptive control when processing falls behind."""
        if actual_fps <= 0:
            return
        if actual_fps < self.target_fps * 0.8:
            self.set_rate(max(actual_fps * 0.9, 1.0))


class FileTailWatcher:
    """Watch a file for appended lines and call a callback for each line."""

    def __init__(self, filepath: str, callback: Callable[[str], None]):
        self.filepath = Path(filepath)
        self.callback = callback
        self._position = 0
        self._observer = None
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_watching(self) -> None:
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")

        self._position = self.filepath.stat().st_size
        self._stop_event.clear()

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except Exception:
            logger.warning("watchdog unavailable; falling back to polling file tail")
            self._start_polling()
            return

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):  # type: ignore[override]
                if Path(event.src_path) == watcher.filepath:
                    watcher._read_new_lines()

        self._observer = Observer()
        self._observer.schedule(_Handler(), str(self.filepath.parent), recursive=False)
        self._observer.start()

    def stop_watching(self) -> None:
        self._stop_event.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None

    def _start_polling(self) -> None:
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            self._read_new_lines()
            time.sleep(0.5)

    def _read_new_lines(self) -> None:
        with self.filepath.open("r", encoding="utf-8", newline="") as handle:
            handle.seek(self._position)
            for line in handle:
                line = line.strip()
                if line:
                    self.callback(line)
            self._position = handle.tell()


class StreamingSimulator:
    """CSV and file-tail streaming simulator for the NIDS pipeline."""

    def __init__(
        self,
        pipeline: Pipeline,
        data_source: str,
        flows_per_second: float = 100.0,
        mode: str = "csv",
        repeat: bool = False,
        max_flows: Optional[int] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        if mode not in {"csv", "tail"}:
            raise ValueError("mode must be either 'csv' or 'tail'")

        self.pipeline = pipeline
        self.data_source = Path(data_source)
        self.mode = mode
        self.repeat = repeat
        self.max_flows = max_flows
        self.event_callback = event_callback
        self.rate_controller = FlowRateController(flows_per_second)
        self.stats = StreamingStats(target_fps=flows_per_second)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tail_watcher: Optional[FileTailWatcher] = None
        self._tail_headers: Optional[List[str]] = None

    def set_flow_rate(self, fps: float) -> None:
        self.rate_controller.set_rate(fps)
        self.stats.target_fps = fps

    def start(self, block: bool = True) -> None:
        if not self.data_source.exists():
            raise FileNotFoundError(f"Data source not found: {self.data_source}")

        self._running = True
        target = self._run_csv if self.mode == "csv" else self._run_tail

        if block:
            target()
            return

        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._tail_watcher is not None:
            self._tail_watcher.stop_watching()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.to_dict()

    def _run_csv(self) -> None:
        while self._running:
            for row in self._iter_csv_rows():
                if not self._running:
                    break
                self._process_row(row)
                if self.max_flows and self.stats.total_flows_processed >= self.max_flows:
                    self._running = False
                    break

            if not self.repeat:
                self._running = False

    def _run_tail(self) -> None:
        self._tail_headers = self._read_headers()

        def on_line(line: str) -> None:
            if not self._running:
                return
            row_values = next(csv.reader([line]))
            row = dict(zip(self._tail_headers or [], row_values))
            self._process_row(row)

        self._tail_watcher = FileTailWatcher(str(self.data_source), on_line)
        self._tail_watcher.start_watching()

        try:
            while self._running:
                if self.max_flows and self.stats.total_flows_processed >= self.max_flows:
                    self._running = False
                    break
                time.sleep(0.25)
        finally:
            self._tail_watcher.stop_watching()

    def _read_headers(self) -> List[str]:
        with self.data_source.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            try:
                return next(reader)
            except StopIteration:
                raise ValueError(f"CSV file is empty: {self.data_source}")

    def _iter_csv_rows(self) -> Iterable[Dict[str, Any]]:
        with self.data_source.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"CSV file has no header row: {self.data_source}")
            for row in reader:
                yield row

    def _process_row(self, row: Dict[str, Any]) -> Optional[Alert]:
        self.rate_controller.wait_for_next_flow()
        started = time.perf_counter()
        flow = network_flow_from_row(row)
        alert = self.pipeline.process_flow(flow)
        latency_ms = (time.perf_counter() - started) * 1000
        self.stats.record(latency_ms, alert)

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "latency_ms": latency_ms,
            "flow_features": dict(zip(FEATURE_COLUMNS, flow.to_features().tolist())),
            "src_ip": flow.src_ip,
            "dst_ip": flow.dst_ip,
            "alert": alert.to_dict() if alert else None,
            "stats": self.stats.to_dict(),
        }
        if self.event_callback:
            self.event_callback(event)

        if self.stats.total_flows_processed % 1000 == 0:
            logger.info("Streaming progress", extra={"stats": json.dumps(self.stats.to_dict())})

        return alert
