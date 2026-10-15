#!/usr/bin/env python3
"""Snapshot AI/ML-keyword ClinicalTrials.gov candidates for manual curation.

This is a discovery feed, not an AI-drug cohort: registry keyword matches can
cover AI as the intervention, a clinical workflow tool, or incidental text.
Raw API records and the manifest are written under ignored data/raw/ by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = "https://clinicaltrials.gov/api/v2"
DEFAULT_QUERY = '"artificial intelligence" OR "machine learning" OR "deep learning" OR "generative AI"'
FIELDS = ",".join((
    "NCTId", "BriefTitle", "OfficialTitle", "StudyType", "Phase", "OverallStatus",
    "StudyFirstPostDate", "StartDate", "PrimaryCompletionDate", "CompletionDate",
    "ResultsFirstPostDate", "Condition", "InterventionName", "PrimaryOutcomeMeasure",
    "LeadSponsorName", "LeadSponsorClass", "ReferencePMID",
))


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "QuantLabAI/0.1 research; contact research@castalia.institute"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default=DEFAULT_QUERY, help="ClinicalTrials.gov v2 query.term; retain it in the manifest")
    parser.add_argument("--page-size", type=int, default=100, help="API page size (1–1000); moderate pages keep public API responses manageable")
    parser.add_argument("--max-pages", type=int, default=50, help="Safety cap; manifest marks a capped/incomplete fetch")
    parser.add_argument("--pause", type=float, default=0.2)
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/ai_trial_candidates.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/ai_trial_candidates.manifest.json")
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000 or args.max_pages < 1 or args.pause < 0:
        raise SystemExit("page-size must be 1–1000, max-pages positive, and pause non-negative")

    version = fetch_json(f"{API}/version")
    query: dict[str, str] = {
        "format": "json", "query.term": args.query, "pageSize": str(args.page_size),
        "countTotal": "true", "fields": FIELDS,
    }
    records: dict[str, dict] = {}
    pages = 0
    capped = False
    token = ""
    reported_total: int | None = None
    while pages < args.max_pages:
        if token:
            query["pageToken"] = token
        url = f"{API}/studies?{urllib.parse.urlencode(query)}"
        page = fetch_json(url)
        pages += 1
        if reported_total is None:
            reported_total = page.get("totalCount")
        for record in page.get("studies", []):
            protocol = record.get("protocolSection", {})
            nct_id = protocol.get("identificationModule", {}).get("nctId")
            if nct_id:
                records[nct_id] = record
        print(
            f"ClinicalTrials.gov page {pages}: {len(records)} unique candidates collected"
            f" / {page.get('totalCount', 'unknown')} reported",
            file=sys.stderr,
            flush=True,
        )
        token = page.get("nextPageToken", "")
        if not token:
            break
        time.sleep(args.pause)
    else:
        capped = bool(token)
    version_after = fetch_json(f"{API}/version")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(records[key], sort_keys=True, separators=(",", ":")) for key in sorted(records)]
    content = ("\n".join(lines) + "\n") if lines else ""
    args.output.write_text(content, encoding="utf-8")
    manifest = {
        "source": "ClinicalTrials.gov API v2",
        "endpoint": f"{API}/studies",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_version": version.get("apiVersion"),
        "registry_data_timestamp_before": version.get("dataTimestamp"),
        "registry_data_timestamp_after": version_after.get("dataTimestamp"),
        "registry_snapshot_consistent": version.get("dataTimestamp") == version_after.get("dataTimestamp"),
        "query_term": args.query,
        "fields": FIELDS.split(","),
        "page_size": args.page_size,
        "max_pages": args.max_pages,
        "pages_fetched": pages,
        "total_studies_reported": reported_total,
        "unique_candidate_records": len(records),
        "fetch_capped_or_incomplete": bool(
            capped
            or (reported_total is not None and len(records) < reported_total)
            or version.get("dataTimestamp") != version_after.get("dataTimestamp")
        ),
        "jsonl_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "interpretation": "Keyword discovery candidates only; manually classify AI application, role, public-availability time, and primary-source support before analysis.",
        "snapshot_limitation": "API returns current study records. Use the registry's historical record versions and original disclosure sources for point-in-time claims.",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} unique AI/ML-keyword study candidates across {pages} API page(s) to {args.output}")
    if capped:
        print("Warning: page cap reached; this snapshot is incomplete.")
    print("Candidates are not a curated AI-drug-development cohort; inspect the manifest before use.")


if __name__ == "__main__":
    main()
