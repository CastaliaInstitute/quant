#!/usr/bin/env python3
"""Create a small public audit of the local trial/publication/event source join."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--events", type=Path, default=ROOT / "data/biopharma/public_events.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "book/_static/biopharma-source-audit.json")
    args = parser.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text(encoding="utf-8"))
    trials = pd.read_csv(args.input / "trials.csv").fillna("")
    papers = pd.read_csv(args.input / "publications.csv").fillna("")
    sec_path = args.input / "sec_filings.csv"
    sec = pd.read_csv(sec_path).fillna("") if sec_path.exists() else pd.DataFrame()
    events = pd.read_csv(args.events).fillna("")
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
            "source_url": event["source_url"],
            "event_type": event["event_type"],
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
            "historical_price_bar_count": 0,
        },
        "events": event_rows,
        "interpretation": "Registry result-post dates can lag public issuer readouts by years; current trial fields and current linked references are hindsight annotations, not historical model inputs.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote source audit: {args.output}")
    print(f"Trial records={len(trials)}; linked article metadata={len(papers)}; SEC filing metadata={len(sec)}; issuer events={len(events)}; price bars=0")


if __name__ == "__main__":
    main()
