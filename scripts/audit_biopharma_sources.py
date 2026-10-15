#!/usr/bin/env python3
"""Create a small public audit of the local trial/publication/event source join."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def validate_event_catalog(events: pd.DataFrame, universe_path: Path) -> dict[str, object]:
    required = {
        "event_id", "ticker", "issuer", "nct_id", "event_date", "event_time_local",
        "event_timezone", "event_type", "source_url", "time_precision",
        "related_nct_ids", "related_tickers",
    }
    missing = sorted(required - set(events.columns))
    if missing:
        raise SystemExit(f"Event catalog is missing required columns: {', '.join(missing)}")
    for column in ("event_id", "ticker", "issuer", "nct_id", "event_type", "source_url", "time_precision"):
        values = events[column].astype(str).str.strip()
        if values.eq("").any():
            raise SystemExit(f"Event catalog column {column!r} contains an empty value")
    if events.event_id.astype(str).str.strip().duplicated().any():
        raise SystemExit("Event catalog contains duplicate event_id values")
    if not events.time_precision.isin({"date_only", "date_and_time"}).all():
        raise SystemExit("Event catalog time_precision must be date_only or date_and_time")
    parsed_dates = pd.to_datetime(events.event_date, format="%Y-%m-%d", errors="coerce")
    if parsed_dates.isna().any():
        raise SystemExit("Event catalog event_date must use valid YYYY-MM-DD dates")
    for row in events.itertuples(index=False):
        local_time = str(row.event_time_local or "").strip()
        timezone_name = str(row.event_timezone or "").strip()
        if row.time_precision == "date_only":
            if local_time or timezone_name:
                raise SystemExit(f"{row.event_id}: date_only rows must not contain an invented time or timezone")
        else:
            if not local_time or not timezone_name:
                raise SystemExit(f"{row.event_id}: date_and_time rows require both local time and timezone")
            try:
                datetime.strptime(f"{row.event_date} {local_time}", "%Y-%m-%d %H:%M")
                ZoneInfo(timezone_name)
            except (ValueError, ZoneInfoNotFoundError) as exc:
                raise SystemExit(f"{row.event_id}: invalid local event timestamp or IANA timezone") from exc
    if not universe_path.exists():
        raise SystemExit(f"Trial-to-issuer universe not found: {universe_path}")
    universe = pd.read_csv(universe_path, dtype=str).fillna("")
    if not {"nct_id", "ticker"}.issubset(universe.columns):
        raise SystemExit("Trial-to-issuer universe requires nct_id and ticker columns")
    nct_values = universe.nct_id.astype(str).str.strip().str.upper()
    if nct_values.eq("").any() or nct_values.duplicated().any():
        raise SystemExit("Trial-to-issuer universe contains empty or duplicate nct_id values")
    known_trials = set(nct_values)
    unmapped = sorted(set(events.nct_id.astype(str).str.upper()) - known_trials)
    related_trials = {
        part.strip().upper()
        for value in events.related_nct_ids.astype(str)
        for part in value.replace(";", ",").split(",")
        if part.strip()
    }
    unmapped_related = sorted(related_trials - known_trials)
    if unmapped or unmapped_related:
        missing_ids = sorted(set(unmapped + unmapped_related))
        raise SystemExit("Event catalog contains trial IDs absent from universe.csv: " + ", ".join(missing_ids))
    return {
        "event_count": int(len(events)),
        "unique_event_ids": int(events.event_id.nunique()),
        "primary_tickers": sorted(events.ticker.astype(str).str.strip().str.upper().unique().tolist()),
        "time_precision_counts": events.time_precision.value_counts().sort_index().to_dict(),
        "mapped_primary_trial_ids": int(events.nct_id.nunique()),
        "mapped_related_trial_ids": int(len(related_trials)),
    }


def _price_data_audit(path: Path, manifest_path: Path, events: pd.DataFrame) -> dict[str, object]:
    """Summarize a local licensed export without copying its observations."""
    related_symbols: set[str] = set()
    if "related_tickers" in events:
        for value in events.related_tickers.astype(str):
            related_symbols.update(
                part.strip().upper() for part in value.replace(";", ",").split(",") if part.strip()
            )
    required_symbols = sorted({"SPY", "XBI"} | set(
        events.ticker.astype(str).str.strip().str.upper().replace("", pd.NA).dropna()
    ) | related_symbols)
    base: dict[str, object] = {
        "available": path.exists(),
        "manifest_available": manifest_path.exists(),
        "status": "missing",
        "valid_rows": 0,
        "symbols": [],
        "required_symbols": required_symbols,
        "missing_required_symbols": required_symbols,
        "duplicate_symbol_date_rows": 0,
        "non_positive_price_rows": 0,
        "date_range": {"first": None, "last": None},
        "sha256": None,
        "manifest_checksum_matches": None,
    }
    if not path.exists():
        return base

    prices = pd.read_csv(path)
    required_columns = {"date", "symbol", "adjusted_close"}
    missing_columns = sorted(required_columns - set(prices.columns))
    if missing_columns:
        base.update({"status": "invalid", "missing_columns": missing_columns})
        return base

    prices["date"] = pd.to_datetime(prices.date, errors="coerce")
    prices["symbol"] = prices.symbol.astype(str).str.strip().str.upper()
    prices["adjusted_close"] = pd.to_numeric(prices.adjusted_close, errors="coerce")
    base["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    base["valid_rows"] = int(prices.dropna(subset=["date", "symbol", "adjusted_close"]).shape[0])
    base["symbols"] = sorted(prices.loc[prices.symbol.ne(""), "symbol"].dropna().unique().tolist())
    base["duplicate_symbol_date_rows"] = int(prices.duplicated(["symbol", "date"], keep=False).sum())
    base["non_positive_price_rows"] = int(prices.adjusted_close.le(0).sum())
    valid_dates = prices.date.dropna()
    if len(valid_dates):
        base["date_range"] = {
            "first": valid_dates.min().date().isoformat(),
            "last": valid_dates.max().date().isoformat(),
        }
    base["missing_required_symbols"] = sorted(set(required_symbols) - set(base["symbols"]))
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        base["manifest_checksum_matches"] = manifest.get("csv_sha256") == base["sha256"]
        base["provider_manifest"] = {
            key: manifest.get(key)
            for key in ("provider", "retrieved_at_utc", "symbols", "start", "end", "timeframe", "feed", "adjustment", "pages", "bar_count")
        }
    valid = (
        base["valid_rows"] == len(prices)
        and base["duplicate_symbol_date_rows"] == 0
        and base["non_positive_price_rows"] == 0
        and not base["missing_required_symbols"]
        and manifest_path.exists()
        and base["manifest_checksum_matches"] is True
    )
    base["status"] = "ready" if valid else "invalid_or_incomplete"
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--events", type=Path, default=ROOT / "data/biopharma/public_events.csv")
    parser.add_argument("--universe", type=Path, default=ROOT / "data/biopharma/universe.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "book/_static/biopharma-source-audit.json")
    args = parser.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text(encoding="utf-8"))
    trials = pd.read_csv(args.input / "trials.csv").fillna("")
    papers = pd.read_csv(args.input / "publications.csv").fillna("")
    sec_path = args.input / "sec_filings.csv"
    sec = pd.read_csv(sec_path).fillna("") if sec_path.exists() else pd.DataFrame()
    events = pd.read_csv(args.events).fillna("")
    event_catalog_audit = validate_event_catalog(events, args.universe)
    if manifest.get("public_event_catalog_sha256") != hashlib.sha256(args.events.read_bytes()).hexdigest():
        raise SystemExit("Raw source manifest is stale for the public event catalog; rerun scripts/ingest_biopharma.py")
    if manifest.get("universe_sha256") != hashlib.sha256(args.universe.read_bytes()).hexdigest():
        raise SystemExit("Raw source manifest is stale for the trial-to-issuer universe; rerun scripts/ingest_biopharma.py")
    price_path = args.input / "market_prices.csv"
    price_audit = _price_data_audit(price_path, args.input / "market-data-manifest.json", events)
    trial_map = trials.set_index("nct_id").to_dict("index")
    paper_dates = {
        str(row.pmid): pd.to_datetime(row.first_publication_date, errors="coerce")
        for row in papers.itertuples()
    }
    event_rows: list[dict] = []
    for event in events.to_dict("records"):
        trial = trial_map.get(event["nct_id"], {})
        result_post = trial.get("results_first_post_date") or None
        lag_days = None
        if result_post:
            lag_days = (date.fromisoformat(result_post) - date.fromisoformat(event["event_date"])).days
        pmids = [value for value in str(trial.get("linked_pmids", "")).split("|") if value]
        linked_dates = [paper_dates[pmid] for pmid in pmids if pmid in paper_dates and not pd.isna(paper_dates[pmid])]
        event_date = pd.Timestamp(event["event_date"])
        event_rows.append({
            "event_id": event["event_id"],
            "issuer": event["issuer"],
            "ticker": event["ticker"],
            "nct_id": event["nct_id"],
            "issuer_disclosure_date": event["event_date"],
            "timestamp_precision": event["time_precision"],
            "trial_first_post_date": trial.get("study_first_post_date") or None,
            "trial_primary_completion_date": trial.get("primary_completion_date") or None,
            "current_registry_results_first_post_date": result_post,
            "days_from_public_disclosure_to_registry_results_post": lag_days,
            "linked_pubmed_ids_in_current_record": len(pmids),
            "current_linked_papers_dated_on_or_before_event_hindsight_annotation": sum(stamp.date() <= event_date.date() for stamp in linked_dates),
            "current_linked_papers_dated_after_event_hindsight_annotation": sum(stamp.date() > event_date.date() for stamp in linked_dates),
            # The public event ledger is manually curated and is the authority
            # for the disclosure source. Trial registries do not preserve the
            # issuer's original release URL or its first-public timestamp.
            "source_url": event["source_url"],
            "event_type": event["event_type"],
            "related_nct_ids": event.get("related_nct_ids", ""),
            "related_tickers": event.get("related_tickers", ""),
            "curation_note": event.get("curation_note", ""),
        })
    output = {
        "evidence_status": "source_lineage_audit_only_no_price_join_or_model_fit",
        "generated_from_local_source_pull": {
            "retrieved_at_utc": manifest["retrieved_at_utc"],
            "clinicaltrials_gov_api_version": manifest["clinicaltrials_gov_api_version"],
            "clinicaltrials_gov_data_timestamp": manifest["clinicaltrials_gov_data_timestamp"],
            "universe_sha256": manifest["universe_sha256"],
            "current_trial_record_count": int(len(trials)),
            "current_linked_pubmed_reference_count": int(sum(len(str(value).split("|")) for value in trials["linked_pmids"] if value)),
            "europe_pmc_article_metadata_count": int(len(papers)),
            "sec_8k_6k_filing_metadata_count": int(len(sec)),
            "sec_filing_ticker_count": int(sec.ticker.nunique()) if not sec.empty else 0,
            "sec_filing_timestamp_precision_counts": sec.availability_precision.value_counts().to_dict() if "availability_precision" in sec else {},
            "sec_filing_date_range": {
                "first": str(sec.filing_date.min()) if not sec.empty else None,
                "last": str(sec.filing_date.max()) if not sec.empty else None,
            },
            "sec_filings_sha256": hashlib.sha256(sec_path.read_bytes()).hexdigest() if sec_path.exists() else None,
            "issuer_event_source_count": int(len(events)),
            "event_catalog_audit": event_catalog_audit,
            "historical_price_bar_count": int(price_audit["valid_rows"]),
            "market_price_data": price_audit,
        },
        "events": event_rows,
        "interpretation": "Registry result-post dates can lag public issuer readouts by years; current trial fields and current linked references are hindsight annotations, not historical model inputs.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote source audit: {args.output}")
    print(
        f"Trial records={len(trials)}; linked article metadata={len(papers)}; "
        f"SEC filing metadata={len(sec)}; issuer events={len(events)}; "
        f"price bars={output['generated_from_local_source_pull']['historical_price_bar_count']} "
        f"({price_audit['status']})"
    )


if __name__ == "__main__":
    main()
