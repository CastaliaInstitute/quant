#!/usr/bin/env python3
"""Run a gated chronological event-risk evaluation on a local event panel."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from quantlab.event_risk import walk_forward_event_risk


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "data/processed/event_panel.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/event-risk")
    parser.add_argument("--minimum-training-events", type=int, default=30)
    parser.add_argument("--minimum-test-events", type=int, default=8)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--target", default="down_10pct_event_window", help="binary event-panel target column")
    args = parser.parse_args()
    if not args.panel.exists():
        raise SystemExit(f"Event panel not found: {args.panel}; build it from licensed local prices first.")
    panel = pd.read_csv(args.panel)
    try:
        result = walk_forward_event_risk(
            panel,
            target=args.target,
            minimum_training_events=args.minimum_training_events,
            minimum_test_events=args.minimum_test_events,
            folds=args.folds,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.summary["source_panel_sha256"] = hashlib.sha256(args.panel.read_bytes()).hexdigest()
    result.summary["source_panel_rows"] = int(len(panel))
    result.summary["target"] = args.target
    result.summary["source_panel_event_date_range"] = {
        "first": str(pd.to_datetime(panel.event_date, errors="coerce").min().date()),
        "last": str(pd.to_datetime(panel.event_date, errors="coerce").max().date()),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(result.summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    result.fold_metrics.to_json(args.output_dir / "fold-metrics.json", orient="records", indent=2)
    result.predictions.to_csv(args.output_dir / "oos-predictions.csv", index=False)
    result.calibration.to_csv(args.output_dir / "calibration.csv", index=False)
    print(f"Wrote development-only walk-forward report to {args.output_dir}")
    print("The untouched final chronological holdout is excluded from all reported scores.")


if __name__ == "__main__":
    main()
