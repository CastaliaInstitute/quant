#!/usr/bin/env python3
"""Audit whether local biopharma data can support a chronological RL replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def chronological_counts(events: pd.DataFrame) -> dict[str, object]:
    parsed = pd.to_datetime(events.event_date, errors="coerce").dt.strftime("%Y-%m-%d")
    dates = sorted(parsed.dropna().unique())
    if not dates:
        return {
            "date_clusters": 0,
            "train": {"events": 0, "dates": 0},
            "validation": {"events": 0, "dates": 0},
            "final_test": {"events": 0, "dates": 0},
        }
    train_end = max(1, int(len(dates) * 0.60))
    validation_end = max(train_end + 1, int(len(dates) * 0.80))
    validation_end = min(validation_end, len(dates))
    blocks = {
        "train": set(dates[:train_end]),
        "validation": set(dates[train_end:validation_end]),
        "final_test": set(dates[validation_end:]),
    }
    counts = {
        name: {"events": int(parsed.isin(block).sum()), "dates": int(len(block))}
        for name, block in blocks.items()
    }
    return {"date_clusters": len(dates), **counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=ROOT / "data/biopharma/public_events.csv")
    parser.add_argument("--prices", type=Path, default=ROOT / "data/raw/market_prices.csv")
    parser.add_argument("--panel", type=Path, default=ROOT / "data/processed/event_panel.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "book/_static/rl-replay-readiness.json")
    parser.add_argument("--minimum-train-events", type=int, default=30)
    parser.add_argument("--minimum-validation-events", type=int, default=8)
    parser.add_argument("--minimum-test-events", type=int, default=8)
    parser.add_argument("--minimum-issuers", type=int, default=10)
    args = parser.parse_args()
    if min(args.minimum_train_events, args.minimum_validation_events, args.minimum_test_events, args.minimum_issuers) <= 0:
        raise SystemExit("all minimum sample gates must be positive")

    events = pd.read_csv(args.events).fillna("") if args.events.exists() else pd.DataFrame()
    if not {"event_id", "ticker", "event_date", "source_url", "time_precision"}.issubset(events.columns):
        raise SystemExit("Event ledger needs event_id, ticker, event_date, source_url, and time_precision")
    source_splits = chronological_counts(events)

    prices_exists = args.prices.exists()
    price_check: dict[str, object] = {
        "available": prices_exists,
        "adjusted_close_column": False,
        "valid_rows": 0,
        "symbols": 0,
        "status": "missing",
    }
    if prices_exists:
        prices = pd.read_csv(args.prices)
        required = {"date", "symbol", "adjusted_close"}
        missing = sorted(required - set(prices.columns))
        if missing:
            price_check.update({"status": "invalid", "missing_columns": missing})
        else:
            prices["date"] = pd.to_datetime(prices.date, errors="coerce")
            prices["symbol"] = prices.symbol.astype(str).str.upper()
            prices["adjusted_close"] = pd.to_numeric(prices.adjusted_close, errors="coerce")
            valid = prices.dropna(subset=["date", "symbol", "adjusted_close"])
            positive = valid.adjusted_close.gt(0).all()
            unique = not valid.duplicated(["date", "symbol"]).any()
            price_check.update({
                "adjusted_close_column": True,
                "valid_rows": int(len(valid)),
                "symbols": int(valid.symbol.nunique()),
                "positive_prices": bool(positive),
                "unique_symbol_dates": bool(unique),
                "status": "ready" if positive and unique and len(valid) else "invalid",
            })

    panel_exists = args.panel.exists()
    panel_check: dict[str, object] = {"available": panel_exists, "rows": 0, "status": "missing"}
    if panel_exists:
        panel = pd.read_csv(args.panel)
        required = {"event_id", "ticker", "event_date", "matched_first_session", "matched_second_session", "price_field_used"}
        missing = sorted(required - set(panel.columns))
        if missing:
            panel_check.update({"status": "invalid", "missing_columns": missing})
        else:
            adjusted = panel.price_field_used.astype(str).eq("adjusted_close")
            source_event_ids = set(events.event_id.astype(str))
            panel_event_ids = set(panel.event_id.astype(str))
            panel_check.update({
                "rows": int(len(panel)),
                "unique_event_ids": int(panel.event_id.nunique()),
                "source_events_without_panel_rows": int(len(source_event_ids - panel_event_ids)),
                "adjusted_price_rows": int(adjusted.sum()),
                "status": "ready" if len(panel) and adjusted.all() else "invalid_or_unadjusted",
            })

    panel_for_split = panel if panel_exists and panel_check["status"] == "ready" else pd.DataFrame(columns=["event_date"])
    panel_splits = chronological_counts(panel_for_split)
    issuers = (
        panel.ticker if panel_exists and "ticker" in panel
        else pd.Series(dtype=str)
    ).astype(str).str.strip().str.upper()
    issuer_count = int(issuers[issuers.ne("")].nunique())
    exact_timestamps = int(events.time_precision.astype(str).eq("date_and_time").sum())
    gates = {
        "adjusted_prices_available_and_valid": price_check["status"] == "ready",
        "event_panel_built_with_adjusted_prices": panel_check["status"] == "ready",
        "minimum_train_events": panel_splits["train"]["events"] >= args.minimum_train_events,
        "minimum_validation_events": panel_splits["validation"]["events"] >= args.minimum_validation_events,
        "minimum_final_test_events": panel_splits["final_test"]["events"] >= args.minimum_test_events,
        "minimum_issuer_coverage": issuer_count >= args.minimum_issuers,
    }
    report = {
        "evidence_status": "data_readiness_audit_only_no_policy_fit_or_return_estimate",
        "ready_for_historical_rl_replay": all(gates.values()),
        "input_files": {
            "events": {"available": args.events.exists(), "file": args.events.name},
            "prices": {"available": prices_exists, "file": args.prices.name},
            "event_panel": {"available": panel_exists, "file": args.panel.name},
        },
        "event_coverage": {
            "records": int(len(events)),
            "source_ledger_issuers": int(events.ticker.astype(str).str.strip().str.upper().replace("", pd.NA).nunique()),
            "matched_panel_issuers": issuer_count,
            "exact_timestamp_records": exact_timestamps,
            "source_ledger_chronological_split": source_splits,
            "matched_panel_chronological_60_20_20_split": panel_splits,
        },
        "price_input": price_check,
        "event_panel": panel_check,
        "minimum_sample_gates": {
            "train_events": args.minimum_train_events,
            "validation_events": args.minimum_validation_events,
            "final_test_events": args.minimum_test_events,
            "issuers": args.minimum_issuers,
        },
        "gates": gates,
        "interpretation": (
            "A passing gate permits a historical replay diagnostic, not a claim of trading edge. "
            "The final chronological block must remain untouched until the protocol and policy are frozen. "
            "Realized disclosure dates must not be supplied as observable event schedules unless a dated pre-event source proves they were known."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote replay-readiness audit: {args.output}")
    print(f"Status={'ready' if report['ready_for_historical_rl_replay'] else 'not_ready'}; gates={sum(gates.values())}/{len(gates)}")


if __name__ == "__main__":
    main()
