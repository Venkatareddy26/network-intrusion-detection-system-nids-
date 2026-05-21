"""Command-line streaming demo for NIDS.

Examples:
    python -m src.nids.streaming.demo --data data/nids_synthetic.csv --fps 25
    python -m src.nids.streaming.demo --data live_flows.csv --mode tail --fps 10
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TextIO

from src.nids.data.loader import FEATURE_COLUMNS
from src.nids.models.classifier import NIDSClassifier
from src.nids.models.explainer import SHAPExplainer
from src.nids.pipeline.processor import Pipeline
from src.nids.streaming.simulator import (
    FlowRateController,
    StreamingSimulator,
    StreamingStats,
    network_flow_from_row,
)

try:
    from colorama import Fore, Style
    from colorama import init as colorama_init

    colorama_init()
except Exception:
    class _NoColor:
        RED = YELLOW = GREEN = CYAN = RESET_ALL = BRIGHT = ""

    Fore = Style = _NoColor()


def build_pipeline(model_path: str) -> Pipeline:
    classifier = NIDSClassifier()
    classifier.load(model_path)
    explainer = SHAPExplainer(classifier.model, FEATURE_COLUMNS)
    return Pipeline(classifier, explainer)


def _open_log(path: Optional[str]) -> Optional[TextIO]:
    if not path:
        return None
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path.open("a", encoding="utf-8")


def _write_event(handle: Optional[TextIO], event: Dict[str, Any]) -> None:
    if handle is None:
        return
    handle.write(json.dumps(event, default=str) + "\n")
    handle.flush()


def _format_features(alert: Dict[str, Any]) -> str:
    features = alert.get("top_3_features", [])[:3]
    parts = []
    for feature in features:
        parts.append(
            f"{feature.get('feature', '?')}={feature.get('value', 0):.2f} "
            f"(imp={feature.get('abs_importance', 0):.4f})"
        )
    return "; ".join(parts)


def _print_event(event: Dict[str, Any]) -> None:
    alert = event.get("alert")
    stats = event.get("stats", {})
    if alert:
        severity_color = Fore.RED if alert.get("severity") == "high" else Fore.YELLOW
        print(
            f"{severity_color}{Style.BRIGHT}[ALERT]{Style.RESET_ALL} "
            f"{alert['attack_type']} conf={alert['confidence']:.1%} "
            f"{event.get('src_ip')} -> {event.get('dst_ip')} "
            f"latency={event.get('latency_ms', 0):.2f}ms"
        )
        feature_text = _format_features(alert)
        if feature_text:
            print(f"  {Fore.CYAN}SHAP:{Style.RESET_ALL} {feature_text}")
    elif stats.get("total_flows_processed", 0) % 100 == 0:
        print(
            f"{Fore.GREEN}[STATS]{Style.RESET_ALL} "
            f"flows={stats.get('total_flows_processed', 0)} "
            f"fps={stats.get('flows_per_second', 0):.1f} "
            f"alerts={stats.get('alerts_generated', 0)} "
            f"p95={stats.get('p95_latency_ms', 0):.2f}ms"
        )


def run_csv_or_tail(args: argparse.Namespace) -> None:
    pipeline = build_pipeline(args.model)
    session_log = _open_log(args.log_file)
    replay_log = _open_log(args.save_replay)

    def on_event(event: Dict[str, Any]) -> None:
        _print_event(event)
        _write_event(session_log, event)
        if event.get("alert") is not None:
            _write_event(replay_log, event)

    simulator = StreamingSimulator(
        pipeline=pipeline,
        data_source=args.data,
        flows_per_second=args.fps,
        mode=args.mode,
        repeat=args.repeat,
        max_flows=args.max_flows,
        event_callback=on_event,
    )

    try:
        print(
            f"Starting NIDS streaming demo: data={args.data}, mode={args.mode}, "
            f"target_fps={args.fps}"
        )
        simulator.start(block=True)
    except KeyboardInterrupt:
        print("\nStopping demo...")
        simulator.stop()
    finally:
        final_stats = simulator.get_stats()
        print(f"Final stats: {json.dumps(final_stats, indent=2)}")
        if session_log:
            session_log.close()
        if replay_log:
            replay_log.close()


def run_replay(args: argparse.Namespace) -> None:
    pipeline = build_pipeline(args.model)
    stats = StreamingStats(target_fps=args.fps)
    rate = FlowRateController(args.fps)
    replay_path = Path(args.replay)
    if not replay_path.exists():
        raise FileNotFoundError(f"Replay file not found: {replay_path}")

    print(f"Replaying attack sequence from {replay_path} at {args.fps} fps")
    with replay_path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            if args.max_flows and idx > args.max_flows:
                break
            event = json.loads(line)
            row = event.get("flow_features", {})
            row["src_ip"] = event.get("src_ip", "0.0.0.0")
            row["dst_ip"] = event.get("dst_ip", "0.0.0.0")
            row["timestamp"] = datetime.utcnow().isoformat()

            rate.wait_for_next_flow()
            started = time.perf_counter()
            alert = pipeline.process_flow(network_flow_from_row(row))
            latency_ms = (time.perf_counter() - started) * 1000
            stats.record(latency_ms, alert)
            _print_event(
                {
                    "latency_ms": latency_ms,
                    "src_ip": row["src_ip"],
                    "dst_ip": row["dst_ip"],
                    "alert": alert.to_dict() if alert else None,
                    "stats": stats.to_dict(),
                }
            )

    print(f"Replay stats: {json.dumps(stats.to_dict(), indent=2)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the NIDS streaming demo")
    parser.add_argument("--data", default="data/nids_synthetic.csv", help="CSV file to stream")
    parser.add_argument("--model", default="models/nids_model.pkl", help="Trained model path")
    parser.add_argument("--mode", choices=["csv", "tail"], default="csv", help="Streaming mode")
    parser.add_argument("--fps", type=float, default=25.0, help="Target flows per second")
    parser.add_argument("--max-flows", type=int, default=None, help="Stop after N flows")
    parser.add_argument("--repeat", action="store_true", help="Loop the CSV source until stopped")
    parser.add_argument("--log-file", default=None, help="Write full session JSONL logs")
    parser.add_argument("--save-replay", default=None, help="Write detected attack events to JSONL")
    parser.add_argument("--replay", default=None, help="Replay a JSONL file produced by --save-replay")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.replay:
        run_replay(args)
    else:
        run_csv_or_tail(args)


if __name__ == "__main__":
    main()
