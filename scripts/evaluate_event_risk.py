#!/usr/bin/env python3
"""Run a gated chronological event-risk evaluation on a local event panel."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from quantlab.event_risk import DEFAULT_FEATURES, walk_forward_event_risk


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "data/processed/event_panel.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/event-risk")
    parser.add_argument("--protocol", type=Path, default=ROOT / "config/biopharma_event_risk_protocol.json")
    parser.add_argument("--minimum-training-events", type=int)
    parser.add_argument("--minimum-test-events", type=int)
    parser.add_argument("--folds", type=int)
    parser.add_argument("--final-holdout-fraction", type=float)
    parser.add_argument("--target", help="primary or predeclared sensitivity target")
    parser.add_argument(
        "--allow-protocol-deviation", action="store_true",
        help="allow and record changes to frozen evaluation settings",
    )
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    protocol_hash = hashlib.sha256(args.protocol.read_bytes()).hexdigest()
    protocol_features = protocol["features"]["fixed_allowlist"]
    if protocol_features != list(DEFAULT_FEATURES):
        raise SystemExit(
            "Protocol feature allowlist differs from the evaluator implementation; "
            "review and version the protocol before running."
        )
    evaluation = protocol["development_evaluation"]
    target_options = protocol["targets"]
    target_roles = {
        target_options["primary"]["column"]: "primary",
        target_options["predeclared_sensitivity"]["column"]: "predeclared_sensitivity",
    }
    target = args.target or target_options["primary"]["column"]
    if target not in target_roles:
        if not args.allow_protocol_deviation:
            raise SystemExit("Target is outside the frozen protocol; pass --allow-protocol-deviation to record it.")
        target_roles[target] = "deviation"
    settings = {
        "minimum_training_events": evaluation["minimum_training_events"],
        "minimum_test_events": evaluation["minimum_test_events_per_fold"],
        "folds": evaluation["folds"],
        "final_holdout_fraction": evaluation["final_holdout_fraction"],
    }
    overrides = {
        "minimum_training_events": args.minimum_training_events,
        "minimum_test_events": args.minimum_test_events,
        "folds": args.folds,
        "final_holdout_fraction": args.final_holdout_fraction,
    }
    deviations: dict[str, dict[str, object]] = {}
    for name, override in overrides.items():
        if override is None:
            continue
        if override != settings[name]:
            deviations[name] = {"protocol_value": settings[name], "used_value": override}
            if not args.allow_protocol_deviation:
                raise SystemExit(
                    f"{name}={override} differs from the frozen protocol value {settings[name]}; "
                    "pass --allow-protocol-deviation to record it."
                )
            settings[name] = override
    if not args.panel.exists():
        raise SystemExit(f"Event panel not found: {args.panel}; build it from licensed local prices first.")
    panel_manifest_path = args.panel.with_suffix(".manifest.json")
    if not panel_manifest_path.exists():
        raise SystemExit(f"Event-panel manifest not found: {panel_manifest_path}; rebuild the panel with its source lineage.")
    panel_manifest_bytes = panel_manifest_path.read_bytes()
    panel_manifest = json.loads(panel_manifest_bytes)
    panel_sha256 = hashlib.sha256(args.panel.read_bytes()).hexdigest()
    if panel_manifest.get("panel_sha256") != panel_sha256:
        raise SystemExit("Event-panel manifest panel_sha256 does not match the panel CSV")
    input_hashes = panel_manifest.get("input_sha256", {})
    input_paths = panel_manifest.get("input_paths", {})
    required_inputs = {"events", "prices", "price_manifest"}
    if not required_inputs.issubset(input_hashes) or not required_inputs.issubset(input_paths):
        raise SystemExit("Event-panel manifest must hash events, prices, and the provider price manifest")
    for name, expected_hash in input_hashes.items():
        source_path = Path(input_paths.get(name, ""))
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        if not source_path.is_file():
            raise SystemExit(f"Event-panel source {name!r} is missing: {source_path}")
        observed_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            raise SystemExit(f"Event-panel source {name!r} changed since panel creation; rebuild the panel")
    price_manifest_path = Path(input_paths["price_manifest"])
    if not price_manifest_path.is_absolute():
        price_manifest_path = ROOT / price_manifest_path
    price_manifest = json.loads(price_manifest_path.read_text(encoding="utf-8"))
    if price_manifest.get("license_review_status") != "approved_for_research":
        raise SystemExit("Price manifest is not marked approved_for_research")
    if price_manifest.get("csv_sha256") != input_hashes["prices"]:
        raise SystemExit("Price manifest checksum does not match the panel's source price file")
    if panel_manifest.get("price_basis") != "adjusted_close":
        raise SystemExit("Frozen protocol requires adjusted_close prices")
    benchmark_values = set(panel_manifest.get("benchmark_symbols", {}).values())
    if not {"SPY", "XBI"}.issubset(benchmark_values):
        raise SystemExit("Frozen protocol requires both SPY and XBI event-study benchmarks")
    panel = pd.read_csv(args.panel)
    feature_policy = protocol["features"]
    fixed_features = [column for column in feature_policy["fixed_allowlist"] if column in panel.columns]
    numeric_prefix = feature_policy["additional_numeric_prefix"]
    numeric_features = sorted(
        column for column in panel.columns
        if column.startswith(numeric_prefix) and column.endswith("_median")
    )
    selected_features = tuple(dict.fromkeys(fixed_features + numeric_features))
    try:
        result = walk_forward_event_risk(
            panel,
            features=selected_features,
            target=target,
            minimum_training_events=settings["minimum_training_events"],
            minimum_test_events=settings["minimum_test_events"],
            folds=settings["folds"],
            final_holdout_fraction=settings["final_holdout_fraction"],
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.summary["source_panel_sha256"] = hashlib.sha256(args.panel.read_bytes()).hexdigest()
    result.summary["source_panel_manifest_sha256"] = hashlib.sha256(panel_manifest_bytes).hexdigest()
    result.summary["source_panel_rows"] = int(len(panel))
    result.summary["target"] = target
    result.summary["protocol"] = {
        "id": protocol["protocol_id"],
        "version": protocol["version"],
        "status": protocol["status"],
        "sha256": protocol_hash,
        "target_role": target_roles[target],
        "deviations": deviations,
        "minimum_training_events": settings["minimum_training_events"],
        "minimum_test_events": settings["minimum_test_events"],
        "folds": settings["folds"],
        "final_holdout_fraction": settings["final_holdout_fraction"],
        "development_oos_features": list(result.summary["features"]),
    }
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
